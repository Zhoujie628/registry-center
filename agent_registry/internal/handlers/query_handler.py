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
from google.protobuf.json_format import MessageToDict

from agent_registry.internal.handlers.base_handler import BaseHandler
from agent_registry.internal.protocols.response import InternalResponse


class QueryHandler(BaseHandler):
    def handle(self, params: Dict[str, Any], registry, config) -> Dict[str, Any]:
        agent_name = params.get('agent_name')
        organization = params.get('organization')
        
        if agent_name and organization:
            agent = registry.find_by_key(agent_name, organization)
            if not agent:
                return InternalResponse(
                    success=False,
                    error="Agent not found",
                    message=f"Agent '{agent_name}' from organization '{organization}' not found"
                ).model_dump()
            
            status = registry.get_status(agent_name, organization)
            if status != 'published':
                return InternalResponse(
                    success=False,
                    error="Agent not published",
                    message=f"Agent '{agent_name}' is not in published status"
                ).model_dump()
            
            agent_dict = MessageToDict(agent, preserving_proto_field_name=True)
            
            return InternalResponse(
                success=True,
                message="Agent retrieved successfully",
                data={"agent": agent_dict}
            ).model_dump()
        
        agents = registry.get_agents_by_status('published')
        
        if organization:
            agents = [a for a in agents if a.provider.organization == organization]
        
        agent_list = []
        for agent in agents:
            agent_dict = MessageToDict(agent, preserving_proto_field_name=True)
            agent_list.append(agent_dict)
        
        return InternalResponse(
            success=True,
            message="Agents retrieved successfully",
            data={"agents": agent_list, "count": len(agent_list)}
        ).model_dump()