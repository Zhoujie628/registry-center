# agent_registry/persistence.py
import json
import os
from typing import List, Dict, Any

from loguru import logger
from pathlib import Path


def save_to_file(file_path: str, agents: List[Dict[str, Any]]) -> None:
    """Save a list of agent dictionaries to a JSON file."""
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(agents, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(agents)} agents to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save agents to {file_path}: {e}")
        raise


def load_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Load agent dictionaries from a JSON file. If file not found, return empty list."""
    if not os.path.exists(file_path):
        logger.warning(f"Persistence file {file_path} not found. Starting with empty registry.")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.error(f"Invalid format in {file_path}: expected a list")
            return []
        logger.info(f"Loaded {len(data)} agents from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load agents from {file_path}: {e}")
        return []