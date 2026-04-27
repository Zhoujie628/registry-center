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
import platform
import socket
from typing import Dict, Any

from loguru import logger


class RegistryClient:
    SOCKET_PATH = "run/registry-center/internal.sock"
    TCP_HOST = "127.0.0.1"
    # cli模拟客户端端口，windows系统下启动必须与uds服务端端口一致
    TCP_PORT = 9302

    def __init__(self, socket_path: str = None, tcp_host: str = None, tcp_port: int = None):
        self.socket_path = socket_path or self.SOCKET_PATH
        self.tcp_host = tcp_host or self.TCP_HOST
        self.tcp_port = tcp_port or self.TCP_PORT
        self._use_tcp = platform.system() == 'Windows'

    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if self._use_tcp:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client_socket.connect((self.tcp_host, self.tcp_port))
            except ConnectionRefusedError:
                return {
                    "success": False,
                    "error": "Connection refused",
                    "message": f"Internal service is not running on {self.tcp_host}:{self.tcp_port}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": "Connection failed",
                    "message": str(e)
                }
        else:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                client_socket.connect(self.socket_path)
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": "Socket not found",
                    "message": "Internal service is not running"
                }
            except PermissionError:
                return {
                    "success": False,
                    "error": "Permission denied",
                    "message": "You don't have permission to access registry center"
                }
            except ConnectionRefusedError:
                return {
                    "success": False,
                    "error": "Connection refused",
                    "message": "Internal service is not accepting connections"
                }
        
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
        request = {
            "action": "approval",
            "params": {
                "agent_name": agent_name,
                "organization": organization
            }
        }
        return self._send_request(request)