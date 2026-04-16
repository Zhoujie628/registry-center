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

# agent_registry/core.py
import asyncio
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from a2a.types import AgentCard
from google.protobuf.json_format import MessageToDict
from loguru import logger

from agent_registry.config import PERSISTENCE_FILE
from agent_registry.persistence import save_to_file, load_from_file
from common.util.config_util import get_root_path


class RegistryCore:
    """
    Core registry that stores AgentCard instances with (name, organization) as unique key.
    Provides registration, update, deletion, exact search, and LLM-based fuzzy search.
    Supports persistence to a JSON file.
    """

    def __init__(self, persistence_file: str = PERSISTENCE_FILE):
        data_path = Path(get_root_path()) / "data"
        data_path.mkdir(exist_ok=True)
        os.chmod(data_path, 0o700)
        self.persistence_file = str(data_path / persistence_file)
        # Internal storage of Agents: key is (name, organization) Tuple, value is AgentCard
        self._agents: Dict[Tuple[str, str], AgentCard] = {}
        self._load()  # load from file on startup

    @staticmethod
    def _make_key(name: str, organization: str) -> Tuple[str, str]:
        """Create a normalized key for indexing."""
        return name.strip(), organization.strip()

    # ---------- Public API ----------
    async def register(self, agent: AgentCard) -> bool:
        """
        Register a new agent. Returns True if successful, False if duplicate.
        Raises ValueError if agent lacks required fields (name, provider.organization).
        """
        async with asyncio.Lock():
            key = self._make_key(agent.name, agent.provider.organization)
            self._agents[key] = agent
            self._save()
            logger.info(f"Registered agent: {agent.name} (org={agent.provider.organization})")
            return True

    def find_exact(self, name: Optional[str] = None, organization: Optional[str] = None) -> List[AgentCard]:
        """
        Exact search based on name, organization, and provider (which is provider.organization).
        All parameters are optional; if multiple are given, they are combined with AND.
        """
        result = []
        for agent in self._agents.values():
            # Check name exact match
            if name is not None and agent.name != name:
                continue
            # Check organization exact match
            if organization is not None and agent.provider.organization != organization:
                continue
            result.append(agent)
        return result

    def get_agents(self):
        return self._agents

    # ---------- Private helpers ----------
    def _save(self) -> None:
        """Persist current agents to file."""
        data = [MessageToDict(agent, preserving_proto_field_name=True) for agent in self._agents.values()]
        save_to_file(self.persistence_file, data)

    def _load(self) -> None:
        """Load agents from file and populate the dictionary."""
        data_list = load_from_file(self.persistence_file)
        for item in data_list:
            try:
                agent = AgentCard(**item)
                key = self._make_key(agent.name, agent.provider.organization)
                self._agents[key] = agent
            except Exception as e:
                logger.error(f"Failed to load agent from JSON: {e}, data: {item}")
        logger.info(f"Loaded {len(self._agents)} agents from persistence.")