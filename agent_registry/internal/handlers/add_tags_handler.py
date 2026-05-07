# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# All Rights Reserved.

from typing import Dict, Any, List
from loguru import logger

from agent_registry.internal.handlers.base_handler import BaseUDSHandler
from agent_registry.internal.protocols.response import InternalResponse


class AddTagsHandler(BaseUDSHandler):
    def handle(self, params: Dict[str, Any], registry, config) -> Dict[str, Any]:
        agent_name = params.get('agent_name')
        organization = params.get('organization')
        tags = params.get('tags', [])
        
        if not agent_name or not organization:
            return InternalResponse(
                success=False,
                error="Missing required params: agent_name or organization"
            ).model_dump()
        
        if not isinstance(tags, list):
            return InternalResponse(
                success=False,
                error="Invalid param type",
                message="tags must be a list"
            ).model_dump()
        
        agent = registry.find_by_key(agent_name, organization)
        if not agent:
            return InternalResponse(
                success=False,
                error="Agent not found",
                message=f"Agent '{agent_name}' from organization '{organization}' not found"
            ).model_dump()
        
        try:
            registry.update_tags(agent_name, organization, tags)
            updated_tags = registry.get_tags(agent_name, organization)
            logger.info(f"Tags added to agent: {agent_name} ({organization}) -> {updated_tags}")
            
            return InternalResponse(
                success=True,
                message="Tags added successfully",
                data={
                    "agent_name": agent_name,
                    "organization": organization,
                    "tag": updated_tags or []
                }
            ).model_dump()
        except Exception as e:
            logger.error(f"Failed to add tags: {e}")
            return InternalResponse(
                success=False,
                error=str(e),
                message="Failed to update tags"
            ).model_dump()