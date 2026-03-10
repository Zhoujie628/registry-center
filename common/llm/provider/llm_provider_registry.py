#!/usr/bin/env python
# -*- coding: utf-8 -*-
from common.llm.config.llm_config import LLMConfig, LLMType
from common.llm.provider.base_llm import BaseLLM


class LLMProviderRegistry:
    def __init__(self):
        self.providers = {}

    def register(self, key, provider_cls):
        self.providers[key] = provider_cls

    def get_provider(self, llm_type: LLMType):
        return self.providers[llm_type]


def register_provider(keys):
    def decorator(cls):
        if isinstance(keys, list):
            for key in keys:
                LLM_REGISTRY.register(key, cls)
        else:
            LLM_REGISTRY.register(keys, cls)
        return cls

    return decorator


LLM_REGISTRY = LLMProviderRegistry()

llm_instance = {str: BaseLLM}


# 获取llm单例，如果已经实例化，则从缓存中拿，如果没有则新创建一个
def get_or_create_llm_instance(config: LLMConfig) -> BaseLLM:
    if config.llm_type in llm_instance:
        return llm_instance[config.llm_type]
    else:
        llm = LLM_REGISTRY.get_provider(config.llm_type)(config)
        llm_instance[config.llm_type] = llm
        return llm
