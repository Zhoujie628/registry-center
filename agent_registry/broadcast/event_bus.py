# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0

"""
In-process event bus bridging the synchronous registry core (worker threads /
event loop handlers) to the asyncio-side dispatcher.

Publishing is always non-blocking: the event is persisted to the outbox
(assigning its registry_version) and then queued for asynchronous dispatch.
Even with broadcasting disabled, events stay in the outbox so subscribers can
reconcile through the /changes endpoint.
"""

import asyncio
import queue
from typing import Optional

from loguru import logger

from agent_registry.broadcast.events import EventType, RegistryEvent, build_event
from agent_registry.broadcast.outbox import OutboxStore


class EventBus:
    def __init__(self, outbox: OutboxStore, dispatch_enabled: bool = False):
        self._outbox = outbox
        self._dispatch_enabled = dispatch_enabled
        self._queue: "queue.Queue[RegistryEvent]" = queue.Queue()
        self._dispatcher = None
        self._consumer_task: Optional[asyncio.Task] = None

    def attach_dispatcher(self, dispatcher) -> None:
        self._dispatcher = dispatcher

    def publish(self, event_type: EventType, data: dict) -> RegistryEvent:
        event = self._outbox.append(build_event(event_type, data, registry_version=0))
        if self._dispatch_enabled and self._dispatcher is not None:
            self._queue.put_nowait(event)
        return event

    async def run_consumer(self, poll_interval: float = 0.05):
        """Drain the cross-thread queue and hand events to the dispatcher."""
        logger.info("Event bus consumer started")
        try:
            while True:
                forwarded = False
                while True:
                    try:
                        event = self._queue.get_nowait()
                    except queue.Empty:
                        break
                    try:
                        self._dispatcher.submit(event)
                    except Exception as e:
                        logger.error(f"Dispatcher failed to accept event {event.event_id}: {e}")
                    forwarded = True
                if not forwarded:
                    await asyncio.sleep(poll_interval)
                else:
                    await asyncio.sleep(0)
        except asyncio.CancelledError:
            logger.info("Event bus consumer stopped")
            raise

    def start_consumer(self) -> None:
        if self._consumer_task is None or self._consumer_task.done():
            self._consumer_task = asyncio.get_running_loop().create_task(self.run_consumer())

    async def stop_consumer(self) -> None:
        if self._consumer_task is not None:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
            self._consumer_task = None
