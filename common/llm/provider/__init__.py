from common.llm.provider.llm_deepseek_chat import DeepSeekChatLLM
from common.llm.provider.llm_qwen3_32b import Qwen3LLM
# llm扩展可在此加入
__ALL__ = [
    Qwen3LLM,
    DeepSeekChatLLM
]
