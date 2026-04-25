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

import argparse
import json
import sys

from agent_registry.internal.client.registry_client import RegistryClient


def main():
    parser = argparse.ArgumentParser(
        description="Registry Center Internal CLI Tool"
    )
    parser.add_argument(
        "action",
        choices=["approval", "config", "stats", "query"],
        help="Action to perform"
    )
    parser.add_argument(
        "--agent-name",
        help="Agent name (for approval/query)"
    )
    parser.add_argument(
        "--organization",
        help="Organization name (for approval/query)"
    )
    parser.add_argument(
        "--config-key",
        help="Configuration key (for config)"
    )
    parser.add_argument(
        "--type",
        default="all",
        choices=["all", "registered", "published"],
        help="Stats type (for stats)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="text",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    client = RegistryClient()
    
    if args.action == "approval":
        if not args.agent_name or not args.organization:
            print("Error: --agent-name and --organization are required for approval")
            sys.exit(1)
        result = client.approval_agent(args.agent_name, args.organization)
    
    elif args.action == "config":
        if not args.config_key:
            print("Error: --config-key is required for config")
            sys.exit(1)
        result = client.get_config(args.config_key)
    
    elif args.action == "stats":
        result = client.get_stats(args.type)
    
    elif args.action == "query":
        result = client.query_agent(args.agent_name, args.organization)
    
    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        if result.get("success"):
            print(f"Success: {result.get('message', 'OK')}")
            if result.get("data"):
                print(f"Data: {json.dumps(result['data'], indent=2)}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Message: {result.get('message', '')}")


if __name__ == "__main__":
    main()