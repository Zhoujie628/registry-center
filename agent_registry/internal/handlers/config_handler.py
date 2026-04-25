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

from typing import Dict, Any

from agent_registry.internal.handlers.base_handler import BaseHandler
from agent_registry.internal.protocols.response import InternalResponse


class ConfigHandler(BaseHandler):
    def handle(self, params: Dict[str, Any], registry, config) -> Dict[str, Any]:
        config_key = params.get('config_key')
        
        if not config_key:
            return InternalResponse(
                success=False,
                error="Missing required param: config_key"
            ).model_dump()
        
        config_value = config.get(config_key)
        if config_value is None:
            return InternalResponse(
                success=False,
                error="Config key not found",
                message=f"Configuration key '{config_key}' does not exist"
            ).model_dump()
        
        return InternalResponse(
            success=True,
            message="Config retrieved successfully",
            data={
                "config_key": config_key,
                "config_value": config_value
            }
        ).model_dump()