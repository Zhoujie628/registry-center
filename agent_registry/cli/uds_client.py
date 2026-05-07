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

"""
CLI UDS Client

Unified socket client for CLI commands to communicate with internal UDS service.
All CLI commands that need internal service access should use this client.

Windows: Uses TCP (127.0.0.1:9302) for local debugging
Linux: Uses UDS (run/registry-center/internal.sock)
"""

import json
import platform
import socket
from typing import Dict, Any, Optional, List

from loguru import logger


class UDSClient:
    """
    Socket Client for CLI

    Communicates with internal service:
    - Linux: Unix Domain Socket
    - Windows: TCP socket (for local debugging)

    All CLI commands should use this client for internal operations.
    """

    SOCKET_PATH = "run/registry-center/internal.sock"
    TCP_HOST = "127.0.0.1"
    TCP_PORT = 9302

    def __init__(self, socket_path: str = None, tcp_host: str = None, tcp_port: int = None):
        self.socket_path = socket_path or self.SOCKET_PATH
        self.tcp_host = tcp_host or self.TCP_HOST
        self.tcp_port = tcp_port or self.TCP_PORT
        self._use_tcp = platform.system() == 'Windows'

    def _connect(self) -> socket.socket:
        """Create and connect socket"""
        if self._use_tcp:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((self.tcp_host, self.tcp_port))
        else:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(self.socket_path)
        return client_socket

    def _handle_connect_error(self, e: Exception) -> Dict[str, Any]:
        """Handle connection errors"""
        if self._use_tcp:
            if isinstance(e, ConnectionRefusedError):
                return {
                    "success": False,
                    "error": "Connection refused",
                    "message": f"Internal service is not running on {self.tcp_host}:{self.tcp_port}"
                }
            else:
                return {
                    "success": False,
                    "error": "Connection failed",
                    "message": str(e)
                }
        else:
            if isinstance(e, FileNotFoundError):
                return {
                    "success": False,
                    "error": "Socket not found",
                    "message": f"Internal service is not running (socket: {self.socket_path})"
                }
            elif isinstance(e, PermissionError):
                return {
                    "success": False,
                    "error": "Permission denied",
                    "message": "You don't have permission to access registry center"
                }
            elif isinstance(e, ConnectionRefusedError):
                return {
                    "success": False,
                    "error": "Connection refused",
                    "message": "Internal service is not accepting connections"
                }
            else:
                return {
                    "success": False,
                    "error": "Connection failed",
                    "message": str(e)
                }

    def send_request(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send request to internal service

        Args:
            action: Action type (e.g., "approval")
            params: Request parameters

        Returns:
            Response dict with success, error, message, data fields
        """
        request = {
            "action": action,
            "params": params
        }

        try:
            client_socket = self._connect()
        except Exception as e:
            return self._handle_connect_error(e)

        try:
            client_socket.send(json.dumps(request).encode('utf-8'))

            response = client_socket.recv(4096)
            result = json.loads(response.decode('utf-8'))

            return result
        except json.JSONDecodeError as e:
            logger.error(f"Invalid response from server: {e}")
            return {
                "success": False,
                "error": "Invalid response",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"Error communicating with server: {e}")
            return {
                "success": False,
                "error": "Communication error",
                "message": str(e)
            }
        finally:
            client_socket.close()

    def approval_agent(self, agent_name: str, organization: str) -> Dict[str, Any]:
        """Approve registered agent"""
        return self.send_request("approval", {
            "agent_name": agent_name,
            "organization": organization
        })

    def get_agent(self, agent_name: str, organization: str) -> Dict[str, Any]:
        """Get single agent metadata (agent_name, organization, status, tag)"""
        return self.send_request("get_agent", {
            "agent_name": agent_name,
            "organization": organization
        })

    def list_agents(self) -> Dict[str, Any]:
        """Get all agents metadata"""
        return self.send_request("list_agents", {})

    def add_tags(self, agent_name: str, organization: str, tags: List[str]) -> Dict[str, Any]:
        """Add tags to agent"""
        return self.send_request("add_tags", {
            "agent_name": agent_name,
            "organization": organization,
            "tags": tags
        })


_client: Optional[UDSClient] = None


def get_uds_client() -> UDSClient:
    """Get global UDS client instance"""
    global _client
    if _client is None:
        _client = UDSClient()
    return _client