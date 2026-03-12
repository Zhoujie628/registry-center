# agent_registry/core.py
import json
from typing import List, Optional, Dict, Any, Tuple
from a2a.types import AgentCard
from loguru import logger

from common.llm.config.llm_config import LLMType, get_llm_config_by_type
from common.llm.provider.llm_provider_registry import get_or_create_llm_instance
from agent_registry.persistence import save_to_file, load_from_file
from agent_registry.config import PERSISTENCE_FILE, DEFAULT_LLM_TYPE
from agent_registry.prompts import build_agent_selection_prompt  # assumed to exist


class RegistryCore:
    """
    Core registry that stores AgentCard instances with (name, organization) as unique key.
    Provides registration, update, deletion, exact search, and LLM-based fuzzy search.
    Supports persistence to a JSON file.
    """

    def __init__(self, llm_type: LLMType = DEFAULT_LLM_TYPE, persistence_file: str = PERSISTENCE_FILE):
        self.llm = get_or_create_llm_instance(get_llm_config_by_type(llm_type))
        self.persistence_file = persistence_file
        # Internal storage: key = (name, organization) tuple, value = AgentCard
        self._agents: Dict[Tuple[str, str], AgentCard] = {}
        self._load()  # load from file on startup

    # ---------- Private helpers ----------
    def _make_key(self, name: str, organization: str) -> Tuple[str, str]:
        """Create a normalized key for indexing."""
        return (name.strip(), organization.strip())

    def _save(self) -> None:
        """Persist current agents to file."""
        data = [agent.model_dump() for agent in self._agents.values()]
        save_to_file(self.persistence_file, data)

    def _load(self) -> None:
        """Load agents from file and populate the dictionary."""
        data_list = load_from_file(self.persistence_file)
        for item in data_list:
            try:
                # Validate required fields
                name = item.get("name")
                provider = item.get("provider")
                if not name or not provider or not provider.get("organization"):
                    logger.warning(f"Skipping invalid agent entry: missing name or provider.organization")
                    continue
                agent = AgentCard(**item)
                key = self._make_key(agent.name, agent.provider.organization)
                self._agents[key] = agent
            except Exception as e:
                logger.error(f"Failed to load agent from JSON: {e}, data: {item}")
        logger.info(f"Loaded {len(self._agents)} agents from persistence.")

    # ---------- Public API ----------
    def register(self, agent: AgentCard) -> bool:
        """
        Register a new agent. Returns True if successful, False if duplicate.
        Raises ValueError if agent lacks required fields (name, provider.organization).
        """
        if not agent.name or not agent.provider or not agent.provider.organization:
            raise ValueError("Agent must have 'name' and 'provider.organization'")

        key = self._make_key(agent.name, agent.provider.organization)
        if key in self._agents:
            logger.info(f"Registration skipped: duplicate agent ({agent.name}, {agent.provider.organization})")
            return False

        self._agents[key] = agent
        self._save()
        logger.info(f"Registered agent: {agent.name} (org={agent.provider.organization})")
        return True

    def update(self, name: str, organization: str, updates: Dict[str, Any], partial: bool = True) -> bool:
        """
        Update an existing agent. The primary key (name, organization) cannot be changed.
        If partial=True, only provided fields are updated (PATCH). If partial=False,
        the entire agent is replaced (PUT), but name/organization must match the key.
        Returns True if successful, False if agent not found.
        """
        key = self._make_key(name, organization)
        existing = self._agents.get(key)
        if not existing:
            logger.info(f"Update failed: agent not found ({name}, {organization})")
            return False

        if partial:
            # Partial update: merge updates into existing dict
            updated_data = existing.model_dump()
            updated_data.update(updates)
            # Ensure primary key fields are not changed
            updated_data["name"] = name
            updated_data["provider"]["organization"] = organization
        else:
            # Full replacement: updates should contain a full AgentCard representation
            updated_data = updates
            # Validate that the name/organization in updates match the key
            if updated_data.get("name") != name or updated_data.get("provider", {}).get("organization") != organization:
                raise ValueError("Cannot change primary key (name or organization) during full update")

        try:
            new_agent = AgentCard(**updated_data)
        except Exception as e:
            logger.error(f"Invalid agent data for update: {e}")
            raise ValueError(f"Invalid agent data: {e}")

        # Replace in storage
        self._agents[key] = new_agent
        self._save()
        logger.info(f"Updated agent: {name} (org={organization})")
        return True

    def deregister(self, name: str, organization: str) -> bool:
        """Remove an agent. Returns True if deleted, False if not found."""
        key = self._make_key(name, organization)
        if key not in self._agents:
            logger.info(f"Deregister failed: agent not found ({name}, {organization})")
            return False
        del self._agents[key]
        self._save()
        logger.info(f"Deregistered agent: {name} (org={organization})")
        return True

    def find_by_task(self, task: str) -> List[AgentCard]:
        """
        Fuzzy search using LLM to match task description with agent capabilities.
        Returns a list of candidate agents (could be empty).
        """
        if not task or not self._agents:
            return []

        # Prepare a summary of each agent for the LLM
        agents_info = []
        for agent in self._agents.values():
            agents_info.append({
                "name": agent.name,
                "description": agent.description,
                "skills": [s.name for s in agent.skills] if agent.skills else []
            })

        try:
            prompt = build_agent_selection_prompt(task, json.dumps(agents_info, ensure_ascii=False, indent=2))
            # Assume LLM returns a list of agent names (string)
            _, selected_names_str = self.llm.ask_llm(prompt)
            # Parse selected_names_str as list of names (simplified: treat as comma-separated)
            selected_names = [n.strip() for n in selected_names_str.split(',') if n.strip()]
        except Exception as e:
            logger.error(f"LLM error during agent selection: {e}")
            return []

        # Filter agents whose names are in the selected list
        # Note: This assumes names are unique across organizations; if not, we need a better key.
        # For simplicity, we use name only, but a more robust approach would include organization.
        # We'll match by name, but if multiple same names exist, all will be returned.
        result = [agent for agent in self._agents.values() if agent.name in selected_names]
        logger.info(f"LLM selected {len(result)} agents for task: {task}")
        return result

    def clear_all(self) -> None:
        """Remove all agents (use with caution)."""
        self._agents.clear()
        self._save()
        logger.info("Cleared all agents.")