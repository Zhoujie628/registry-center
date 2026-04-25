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

import json
import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from agent_registry.internal.registry_service import RegistryCenterService
from agent_registry.internal.client.registry_client import RegistryClient
from agent_registry.registry_instance import get_registry, initialize_registry
from common.util.config_util import get_conf


class LocalDebugger:
    def __init__(self):
        self.service = None
        self.service_thread = None
        self.client = None
        self.registry = None

    def setup(self):
        logger.info("=== Setting up local debug environment ===")
        
        initialize_registry()
        self.registry = get_registry()
        logger.info(f"Registry initialized, total agents: {self.registry.count()}")
        
        self.service = RegistryCenterService()
        self.service_thread = threading.Thread(target=self.service.start, daemon=True)
        self.service_thread.start()
        
        time.sleep(1)
        
        self.client = RegistryClient()
        logger.info("UDS service started and client ready")

    def teardown(self):
        logger.info("=== Tearing down debug environment ===")
        if self.service:
            self.service.stop()
        logger.info("Debug environment cleaned up")

    def test_service_status(self):
        logger.info("\n=== Test 1: Check UDS service status ===")
        
        if os.path.exists(RegistryCenterService.SOCKET_PATH):
            logger.info(f"Socket file exists: {RegistryCenterService.SOCKET_PATH}")
            
            import stat
            mode = os.stat(RegistryCenterService.SOCKET_PATH).st_mode
            logger.info(f"Socket permissions: {stat.S_IMODE(mode):03o}")
        else:
            logger.error(f"Socket file not found: {RegistryCenterService.SOCKET_PATH}")

    def test_stats(self):
        logger.info("\n=== Test 2: Get statistics ===")
        
        result = self.client.get_stats("all")
        logger.info(f"Stats result: {json.dumps(result, indent=2)}")
        
        result = self.client.get_stats("registered")
        logger.info(f"Registered stats: {json.dumps(result, indent=2)}")
        
        result = self.client.get_stats("published")
        logger.info(f"Published stats: {json.dumps(result, indent=2)}")

    def test_config(self):
        logger.info("\n=== Test 3: Get config ===")
        
        config = get_conf()
        approval_enabled = config.get('agent_approval_enabled', 'false')
        logger.info(f"Current agent_approval_enabled: {approval_enabled}")
        
        result = self.client.get_config('agent_approval_enabled')
        logger.info(f"Config result: {json.dumps(result, indent=2)}")

    def test_query(self):
        logger.info("\n=== Test 4: Query agents ===")
        
        result = self.client.query_agent()
        logger.info(f"All agents: {json.dumps(result, indent=2)}")

    def test_register_mock_agent(self):
        logger.info("\n=== Test 5: Register mock agent (for testing) ===")
        
        from a2a.types import AgentCard, AgentProvider
        
        config = get_conf()
        approval_enabled = config.get('agent_approval_enabled', 'false')
        
        mock_agent = AgentCard(
            name="DebugTestAgent",
            provider=AgentProvider(
                organization="DebugOrg",
                url="https://debug.test"
            ),
            description="Debug test agent",
            version="1.0.0",
            url="https://debug-agent.test",
        )
        
        if approval_enabled == 'true':
            mock_agent.status = 'registered'
            logger.info("Approval enabled, agent will be registered with status='registered'")
        else:
            mock_agent.status = 'published'
            logger.info("Approval disabled, agent will be registered with status='published'")
        
        success = self.registry.register(mock_agent)
        logger.info(f"Register result: {success}")
        
        agent = self.registry.find_by_key("DebugTestAgent", "DebugOrg")
        if agent:
            logger.info(f"Agent found: name={agent.name}, status={getattr(agent, 'status', 'N/A')}")

    def test_approval(self):
        logger.info("\n=== Test 6: Test approval action ===")
        
        config = get_conf()
        approval_enabled = config.get('agent_approval_enabled', 'false')
        
        if approval_enabled != 'true':
            logger.warning("Approval function is disabled, skipping approval test")
            
            result = self.client.approval_agent("DebugTestAgent", "DebugOrg")
            logger.info(f"Approval result (should fail): {json.dumps(result, indent=2)}")
            return
        
        agent = self.registry.find_by_key("DebugTestAgent", "DebugOrg")
        if not agent:
            logger.error("Agent not found, please run test_register_mock_agent first")
            return
        
        current_status = getattr(agent, 'status', 'published')
        logger.info(f"Current agent status: {current_status}")
        
        if current_status == 'published':
            logger.info("Agent already published, approval should fail")
            result = self.client.approval_agent("DebugTestAgent", "DebugOrg")
            logger.info(f"Approval result (should fail): {json.dumps(result, indent=2)}")
        else:
            logger.info("Agent is registered, approval should succeed")
            result = self.client.approval_agent("DebugTestAgent", "DebugOrg")
            logger.info(f"Approval result: {json.dumps(result, indent=2)}")
            
            agent = self.registry.find_by_key("DebugTestAgent", "DebugOrg")
            if agent:
                logger.info(f"Agent status after approval: {getattr(agent, 'status', 'N/A')}")

    def test_cleanup_mock_agent(self):
        logger.info("\n=== Test 7: Cleanup mock agent ===")
        
        success = self.registry.deregister("DebugTestAgent", "DebugOrg")
        logger.info(f"Deregister result: {success}")
        
        agent = self.registry.find_by_key("DebugTestAgent", "DebugOrg")
        if agent:
            logger.error("Agent still exists after deregister")
        else:
            logger.info("Agent successfully removed")

    def test_full_flow(self):
        logger.info("\n=== Test 8: Full approval flow ===")
        
        from a2a.types import AgentCard, AgentProvider
        
        config = get_conf()
        approval_enabled = config.get('agent_approval_enabled', 'false')
        
        if approval_enabled != 'true':
            logger.warning("Please set agent_approval_enabled=true in config to test full flow")
            return
        
        flow_agent = AgentCard(
            name="FlowTestAgent",
            provider=AgentProvider(
                organization="FlowOrg",
                url="https://flow.test"
            ),
            description="Flow test agent",
            version="1.0.0",
            url="https://flow-agent.test",
        )
        flow_agent.status = 'registered'
        
        logger.info("Step 1: Register agent with status='registered'")
        self.registry.register(flow_agent)
        
        stats = self.client.get_stats("registered")
        logger.info(f"Registered agents count: {stats.get('data', {}).get('registered', 0)}")
        
        logger.info("Step 2: Approve agent")
        result = self.client.approval_agent("FlowTestAgent", "FlowOrg")
        logger.info(f"Approval result: {json.dumps(result, indent=2)}")
        
        stats = self.client.get_stats("published")
        logger.info(f"Published agents count: {stats.get('data', {}).get('published', 0)}")
        
        logger.info("Step 3: Cleanup")
        self.registry.deregister("FlowTestAgent", "FlowOrg")
        logger.info("Flow test agent removed")

    def run_all_tests(self):
        try:
            self.setup()
            
            self.test_service_status()
            self.test_stats()
            self.test_config()
            self.test_query()
            self.test_register_mock_agent()
            self.test_approval()
            self.test_cleanup_mock_agent()
            self.test_full_flow()
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.teardown()


def interactive_mode():
    logger.info("=== Interactive Debug Mode ===")
    logger.info("Commands:")
    logger.info("  1 - Start UDS service")
    logger.info("  2 - Stop UDS service")
    logger.info("  3 - Get stats")
    logger.info("  4 - Get config")
    logger.info("  5 - Query agents")
    logger.info("  6 - Register mock agent")
    logger.info("  7 - Approve agent")
    logger.info("  8 - Deregister mock agent")
    logger.info("  9 - Run all tests")
    logger.info("  q - Quit")
    
    debugger = LocalDebugger()
    service_running = False
    
    while True:
        try:
            cmd = input("\nEnter command: ").strip().lower()
            
            if cmd == 'q':
                if service_running:
                    debugger.teardown()
                break
            
            elif cmd == '1':
                if not service_running:
                    debugger.setup()
                    service_running = True
                else:
                    logger.info("Service already running")
            
            elif cmd == '2':
                if service_running:
                    debugger.teardown()
                    service_running = False
                else:
                    logger.info("Service not running")
            
            elif cmd == '3':
                debugger.test_stats()
            
            elif cmd == '4':
                debugger.test_config()
            
            elif cmd == '5':
                debugger.test_query()
            
            elif cmd == '6':
                debugger.test_register_mock_agent()
            
            elif cmd == '7':
                debugger.test_approval()
            
            elif cmd == '8':
                debugger.test_cleanup_mock_agent()
            
            elif cmd == '9':
                debugger.run_all_tests()
            
            else:
                logger.info(f"Unknown command: {cmd}")
        
        except KeyboardInterrupt:
            logger.info("\nInterrupted")
            if service_running:
                debugger.teardown()
            break
        except Exception as e:
            logger.error(f"Error: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Internal service local debugger")
    parser.add_argument('--interactive', '-i', action='store_true', help="Run in interactive mode")
    parser.add_argument('--quick', '-q', action='store_true', help="Run quick tests only")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        debugger = LocalDebugger()
        debugger.run_all_tests()


if __name__ == "__main__":
    """
    方式1：运行所有自动测试
    python tests/test_internal_service.py
    # 方式2：交互式调试模式（推荐）
    python tests/test_internal_service.py -i
    # 方式3：快速测试
    python tests/test_internal_service.py -q
    """
    main()