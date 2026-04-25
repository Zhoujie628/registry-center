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


class StatsHandler(BaseHandler):
    def handle(self, params: Dict[str, Any], registry, config) -> Dict[str, Any]:
        stat_type = params.get('type', 'all')
        
        total = registry.count()
        
        registered_count = len(registry.get_agents_by_status('registered'))
        published_count = len(registry.get_agents_by_status('published'))
        
        if stat_type == 'registered':
            return InternalResponse(
                success=True,
                message="Stats retrieved successfully",
                data={"registered": registered_count}
            ).model_dump()
        elif stat_type == 'published':
            return InternalResponse(
                success=True,
                message="Stats retrieved successfully",
                data={"published": published_count}
            ).model_dump()
        else:
            return InternalResponse(
                success=True,
                message="Stats retrieved successfully",
                data={
                    "total": total,
                    "registered": registered_count,
                    "published": published_count
                }
            ).model_dump()