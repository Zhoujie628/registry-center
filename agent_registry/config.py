# agent_registry/config.py
from common.llm.config.llm_config import LLMType

DEFAULT_LLM_TYPE = LLMType.QWEN3_32B
PERSISTENCE_FILE = "./data/agent_registry_data.json"