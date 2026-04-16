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

from abc import ABC

from common.vector_db.embedding_model.config.embedding_config import EmbeddingType, EmbeddingConfig


def embedding_tool_register(keys):
    def decorator(cls):
        if isinstance(keys, list):
            for key in keys:
                EMBEDDING_TOOL_REGISTRY.register(key,cls)
        else:
            EMBEDDING_TOOL_REGISTRY.register(keys,cls)
        return cls

    return decorator

class EmbeddingToolRegistry:
    def __init__(self):
        self.providers = {}

    def register(self,key,provider_cls):
        self.providers[key] = provider_cls

    def get_provider(self,embedding_type: EmbeddingType):
        return self.providers[embedding_type]

EMBEDDING_TOOL_REGISTRY = EmbeddingToolRegistry()

embedding_tool_instance = {}

def get_or_create_embedding_tool_instance(config:EmbeddingConfig):
    return EMBEDDING_TOOL_REGISTRY.get_provider(config.embedding_type)(config.__dict__)