# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
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

"""Core-level tests for RegistryCore.retrieve_by_task.

Covers the LLM-failure degradation path that endpoint-level tests
(test_semantic_query.py) cannot reach: the LLM call happens inside
RegistryCore, and _select_agents_by_llm swallows all exceptions and
returns [] (silently degrades to "no match"). These tests fix that
behavior as an explicit contract; if the degradation policy changes
(e.g. surface an error to the caller), these tests should be updated
together.
"""

import shutil
import tempfile

import pytest
from unittest.mock import MagicMock, patch

from a2a.types import AgentCard

from agent_registry.core import RegistryCore


class TestRetrieveByTask:
    """Unit tests for RegistryCore.retrieve_by_task in file persistence mode."""

    @pytest.fixture
    def temp_dir(self):
        d = tempfile.mkdtemp()
        yield d
        shutil.rmtree(d, ignore_errors=True)

    @pytest.fixture
    def registry(self, temp_dir):
        with patch('agent_registry.core.get_llm_instance', return_value=MagicMock()), \
             patch('agent_registry.core.get_embed_instance', return_value=MagicMock()), \
             patch('agent_registry.core.get_root_path', return_value=temp_dir), \
             patch('agent_registry.config.get_conf', return_value={}), \
             patch('agent_registry.config.get_persistence_conf', return_value={'persistence.mode': 'file'}):
            reg = RegistryCore(
                persistence_file='agentcard.json',
                persistence_metadata_file='agentregistry.json',
                use_vectordb=False,
                persistence_mode='file',
                persistence_conf={}
            )
            yield reg

    def _make_agent(self, name="TestAgent", org="TestOrg", desc="Test agent"):
        data = {
            "name": name,
            "provider": {"organization": org, "url": "https://test.org"},
            "description": desc,
            "version": "1.0.0",
            "skills": [],
            "capabilities": {"streaming": False},
            "default_input_modes": [],
            "default_output_modes": [],
        }
        return AgentCard(**data)

    def test_llm_failure_returns_empty_silently(self, registry):
        # LLM 调用抛异常（如 API key 失效、网络故障）→ 静默降级为空列表，不向上抛错
        registry.register(self._make_agent())
        with patch.object(registry.llm, 'ask_llm', side_effect=RuntimeError("LLM service down")):
            result = registry.retrieve_by_task("find test agents", top_n=5, use_vectordb=False)
        assert result == []

    def test_llm_garbage_response_returns_empty_silently(self, registry):
        # LLM 返回无法解析的内容 → 同样静默降级为空列表
        registry.register(self._make_agent())
        with patch.object(registry.llm, 'ask_llm', return_value=("raw", "not-json-at-all")):
            result = registry.retrieve_by_task("find test agents", top_n=5, use_vectordb=False)
        assert result == []

    def test_empty_task_returns_empty_without_llm_call(self, registry):
        # 空 task 短路返回，不触发 LLM 调用
        registry.register(self._make_agent())
        with patch.object(registry.llm, 'ask_llm') as mock_ask:
            result = registry.retrieve_by_task("", top_n=5, use_vectordb=False)
        assert result == []
        mock_ask.assert_not_called()

    def test_llm_selection_filters_registered_agents(self, registry):
        # 正常路径：LLM 返回的 (name, organization) 对决定哪些卡片命中
        registry.register(self._make_agent("AgentA", "TestOrg", "Agent for task A"))
        registry.register(self._make_agent("AgentB", "TestOrg", "Agent for task B"))
        llm_response = ("raw", '[{"name": "AgentA", "organization": "TestOrg"}]')
        with patch.object(registry.llm, 'ask_llm', return_value=llm_response):
            result = registry.retrieve_by_task("need agent a", top_n=5, use_vectordb=False)
        assert [a.name for a in result] == ["AgentA"]

    def test_no_registered_agents_returns_empty_without_llm_call(self, registry):
        # 注册表为空时短路返回，不触发 LLM 调用
        with patch.object(registry.llm, 'ask_llm') as mock_ask:
            result = registry.retrieve_by_task("find test agents", top_n=5, use_vectordb=False)
        assert result == []
        mock_ask.assert_not_called()
