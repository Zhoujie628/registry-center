# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0

"""
Webhook dispatcher: debounces, rate-limits, signs, and delivers registry
events to subscribed callbacks.

Storm protection (three layers):
1. debounce window coalesces repeated changes of the same agent
2. per-subscription token bucket degrades overflow batches to a SYNC_REQUIRED
   summary event (no data is lost - subscribers reconcile via /changes)
3. per-subscription sequential workers isolate slow subscribers from others
   (ordering is preserved at the cost of intra-subscription parallelism)
"""

import asyncio
import hashlib
import hmac
import json
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import httpx
from loguru import logger

from agent_registry.broadcast.events import (
    EventType,
    RegistryEvent,
    build_sync_required,
    merge_events,
    utc_now_iso,
)
from agent_registry.broadcast.outbox import OutboxStore
from agent_registry.broadcast.subscriptions import Subscription, SubscriptionStore, event_matches


class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = max(rate, 0.1)
        self.capacity = max(capacity, 1.0)
        self.tokens = self.capacity
        self._last_refill = time.monotonic()

    def try_consume(self, amount: float) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self._last_refill) * self.rate)
        self._last_refill = now
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False


@dataclass
class _Worker:
    queue: asyncio.Queue
    task: asyncio.Task


def sign_payload(secret: str, timestamp: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode("utf-8") + body,
                      hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class WebhookDispatcher:
    def __init__(self, subscription_store: SubscriptionStore, outbox: OutboxStore,
                 debounce_window: float = 2.0,
                 max_events_per_second: float = 50.0,
                 webhook_timeout: float = 10.0,
                 max_retries: int = 5,
                 backoff_base: float = 2.0,
                 backoff_max: float = 300.0,
                 retention_days: int = 7,
                 client: Optional[httpx.AsyncClient] = None):
        self._subs = subscription_store
        self._outbox = outbox
        self._debounce_window = debounce_window
        self._max_events_per_second = max_events_per_second
        self._webhook_timeout = webhook_timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._retention_days = retention_days
        self._client = client or httpx.AsyncClient(timeout=webhook_timeout)
        self._owns_client = client is None

        self._buffers: Dict[Tuple[str, str, str, str], RegistryEvent] = {}
        self._workers: Dict[str, _Worker] = {}
        self._buckets: Dict[str, TokenBucket] = {}
        self._flusher_task: Optional[asyncio.Task] = None
        self._cleanup_counter = 0

    # ---------- lifecycle ----------

    def start(self) -> None:
        self._flusher_task = asyncio.get_running_loop().create_task(self._flusher_loop())
        for subscription in self._subs.list_all():
            self._add_worker(subscription)
        self.recover()
        logger.info(f"Dispatcher started with {len(self._workers)} subscription worker(s)")

    async def stop(self) -> None:
        if self._flusher_task is not None:
            self._flusher_task.cancel()
            try:
                await self._flusher_task
            except asyncio.CancelledError:
                pass
            self._flusher_task = None
        for worker in self._workers.values():
            worker.task.cancel()
        for worker in self._workers.values():
            try:
                await worker.task
            except asyncio.CancelledError:
                pass
        self._workers.clear()
        if self._owns_client:
            await self._client.aclose()

    # ---------- subscription management ----------

    def add_subscription(self, subscription: Subscription) -> None:
        self._add_worker(subscription)

    def remove_subscription(self, subscription_id: str) -> None:
        worker = self._workers.pop(subscription_id, None)
        self._buckets.pop(subscription_id, None)
        if worker is not None:
            worker.task.cancel()

    def _add_worker(self, subscription: Subscription) -> None:
        if subscription.subscription_id in self._workers:
            return
        loop = asyncio.get_running_loop()
        worker = _Worker(queue=asyncio.Queue(), task=None)  # type: ignore[arg-type]
        worker.task = loop.create_task(self._worker_loop(subscription.subscription_id, worker.queue))
        self._workers[subscription.subscription_id] = worker
        self._buckets[subscription.subscription_id] = TokenBucket(
            rate=self._max_events_per_second,
            capacity=max(self._max_events_per_second * 2, 100.0),
        )

    # ---------- intake ----------

    def submit(self, event: RegistryEvent) -> None:
        """Buffer an event for every matching subscription (debounce stage)."""
        for subscription in self._subs.list_all():
            if not event_matches(event, subscription):
                continue
            if subscription.subscription_id not in self._workers:
                self._add_worker(subscription)
            # Data events (register/update/deregister) coalesce across types for
            # the same agent; health transitions coalesce separately so a card
            # update never swallows a health change signal.
            kind = "health" if event.event_type == EventType.AGENT_HEALTH_CHANGED else "data"
            key = (subscription.subscription_id, str(event.data.get("name", "")),
                   str(event.data.get("organization", "")), kind)
            buffered = self._buffers.get(key)
            self._buffers[key] = event if buffered is None else merge_events(buffered, event)

    def recover(self) -> None:
        """Re-enqueue pending events after a restart, bypassing the debounce window."""
        pending = self._outbox.list_pending()
        if not pending:
            return
        logger.info(f"Recovering {len(pending)} pending outbox event(s) for dispatch")
        for event in pending:
            for subscription in self._subs.list_all():
                if event_matches(event, subscription) and subscription.subscription_id in self._workers:
                    self._workers[subscription.subscription_id].queue.put_nowait([event])

    async def _flusher_loop(self):
        try:
            while True:
                await asyncio.sleep(self._debounce_window)
                self._flush_buffers()
                self._cleanup_counter += 1
                if self._cleanup_counter >= 3600:  # roughly once per hour
                    self._cleanup_counter = 0
                    try:
                        removed = self._outbox.cleanup(self._retention_days)
                        if removed:
                            logger.info(f"Outbox cleanup removed {removed} event(s)")
                    except Exception as e:
                        logger.warning(f"Outbox cleanup failed: {e}")
        except asyncio.CancelledError:
            raise

    def _flush_buffers(self) -> None:
        if not self._buffers:
            return
        buffered, self._buffers = self._buffers, {}
        per_subscription: Dict[str, List[RegistryEvent]] = {}
        for (subscription_id, _, _, _), event in buffered.items():
            per_subscription.setdefault(subscription_id, []).append(event)
        for subscription_id, events in per_subscription.items():
            worker = self._workers.get(subscription_id)
            if worker is None:
                continue
            events.sort(key=lambda e: e.registry_version)
            worker.queue.put_nowait(events)

    # ---------- delivery ----------

    async def _worker_loop(self, subscription_id: str, queue: asyncio.Queue):
        try:
            while True:
                batch: List[RegistryEvent] = await queue.get()
                try:
                    await self._process_batch(subscription_id, batch)
                except Exception as e:
                    logger.error(f"Batch processing failed for {subscription_id}: {e}")
        except asyncio.CancelledError:
            raise

    async def _process_batch(self, subscription_id: str, batch: List[RegistryEvent]):
        subscription = self._subs.get(subscription_id)
        if subscription is None:
            return
        bucket = self._buckets.setdefault(
            subscription_id,
            TokenBucket(rate=self._max_events_per_second,
                        capacity=max(self._max_events_per_second * 2, 100.0)),
        )
        if not bucket.try_consume(len(batch)):
            logger.warning(f"Rate limit hit for subscription {subscription_id}, "
                           f"degrading {len(batch)} event(s) to SYNC_REQUIRED")
            for event in batch:
                self._outbox.mark_status(event.event_id, "degraded")
            sync_event = build_sync_required(self._outbox.max_version())
            await self._deliver_events(subscription, [sync_event], persist=False)
            return
        delivered = await self._deliver_events(subscription, batch, persist=True)
        status = "dispatched" if delivered else "delivery_failed"
        for event in batch:
            self._outbox.mark_status(event.event_id, status)

    async def _deliver_events(self, subscription: Subscription,
                              events: List[RegistryEvent], persist: bool) -> bool:
        body = json.dumps({
            "subscription_id": subscription.subscription_id,
            "events": [e.to_dict() for e in events],
        }, ensure_ascii=False).encode("utf-8")
        timestamp = str(int(time.time()))
        headers = {
            "Content-Type": "application/json",
            "X-Registry-Event-Id": events[0].event_id,
            "X-Registry-Timestamp": timestamp,
        }
        if subscription.secret:
            headers["X-Registry-Signature"] = sign_payload(subscription.secret, timestamp, body)

        max_attempts = self._max_retries + 1
        for attempt in range(max_attempts):
            try:
                response = await self._client.post(subscription.callback_url, content=body, headers=headers)
                if 200 <= response.status_code < 300:
                    return True
                logger.warning(f"Webhook delivery to {subscription.callback_url} returned "
                               f"{response.status_code} (attempt {attempt + 1}/{max_attempts})")
            except (httpx.HTTPError, OSError) as e:
                logger.warning(f"Webhook delivery to {subscription.callback_url} failed: {e} "
                               f"(attempt {attempt + 1}/{max_attempts})")
            if attempt < max_attempts - 1:
                delay = min(self._backoff_base * (2 ** attempt), self._backoff_max)
                delay = delay * (0.7 + random.random() * 0.6)  # +/-30% jitter
                await asyncio.sleep(delay)
        return False
