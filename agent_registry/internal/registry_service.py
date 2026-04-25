# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import os
import socket
import threading
from typing import Dict, Type

from loguru import logger

from agent_registry.internal.handlers.base_handler import BaseHandler
from agent_registry.internal.handlers.approval_handler import ApprovalHandler
from agent_registry.internal.handlers.config_handler import ConfigHandler
from agent_registry.internal.handlers.stats_handler import StatsHandler
from agent_registry.internal.handlers.query_handler import QueryHandler
from agent_registry.internal.protocols.actions import Action
from agent_registry.registry_instance import get_registry
from common.util.config_util import get_conf


class RequestDispatcher:
    _handlers: Dict[str, Type[BaseHandler]] = {
        Action.APPROVAL: ApprovalHandler,
        Action.CONFIG: ConfigHandler,
        Action.STATS: StatsHandler,
        Action.QUERY: QueryHandler,
    }
    
    def get_handler(self, action: str) -> BaseHandler:
        handler_class = self._handlers.get(action)
        if handler_class:
            return handler_class()
        return None
    
    def register_handler(self, action: str, handler_class: Type[BaseHandler]):
        self._handlers[action] = handler_class


class RegistryCenterService:
    SOCKET_PATH = "run/registry-center/internal.sock"
    SOCKET_DIR = "run/registry-center"
    
    def __init__(self):
        self.socket_path = self.SOCKET_PATH
        self.registry = get_registry()
        self.config = get_conf()
        self.dispatcher = RequestDispatcher()
        self._running = False

    def start(self):
        self._ensure_socket_dir()

        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass

        try:
            server_socket.bind(self.socket_path)
            os.chmod(self.socket_path, 0o660)

            server_socket.listen(5)
            self._running = True
            logger.info(f"Internal service started on UDS socket: {self.socket_path}")

            while self._running:
                try:
                    server_socket.settimeout(1.0)
                    conn, _ = server_socket.accept()
                    thread = threading.Thread(target=self._handle_request, args=(conn,))
                    thread.daemon = True
                    thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        logger.error(f"Error accepting connection: {e}")
        except Exception as e:
            logger.error(f"Failed to start UDS service: {e}")
        finally:
            server_socket.close()
            self._cleanup_socket()
    
    def stop(self):
        self._running = False
        self._cleanup_socket()
    
    def _ensure_socket_dir(self):
        os.makedirs(self.SOCKET_DIR, exist_ok=True)
        os.chmod(self.SOCKET_DIR, 0o750)
    
    def _cleanup_socket(self):
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass
    
    def _handle_request(self, conn):
        try:
            data = conn.recv(4096)
            if not data:
                return
            
            request = json.loads(data.decode('utf-8'))
            action = request.get('action', '')
            params = request.get('params', {})
            
            handler = self.dispatcher.get_handler(action)
            if not handler:
                response = {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
            else:
                response = handler.handle(params, self.registry, self.config)
            
            conn.send(json.dumps(response).encode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON request: {e}")
            response = {"success": False, "error": "Invalid JSON format"}
            conn.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            response = {"success": False, "error": str(e)}
            conn.send(json.dumps(response).encode('utf-8'))
        finally:
            conn.close()