#!/bin/bash

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

# 通过进程名停止服务
# 使用方法: ./stop.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 进程名
PROCESS_NAME="agent_registry.start"

echo "正在停止服务..."

# 查找进程
PIDS=$(pgrep -f "$PROCESS_NAME" 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo -e "${YELLOW}未找到运行中的服务${NC}"
    exit 0
fi

echo "找到进程 PID: $PIDS"

# 停止进程
for PID in $PIDS; do
    kill $PID 2>/dev/null
done

sleep 2

# 检查并强制停止残留进程
PIDS=$(pgrep -f "$PROCESS_NAME" 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}进程未响应，强制停止...${NC}"
    for PID in $PIDS; do
        kill -9 $PID 2>/dev/null
    done
    sleep 1
fi

# 检查是否停止
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}进程未响应，强制停止...${NC}"
    kill -9 $PID 2>/dev/null
    sleep 1
fi

echo -e "${GREEN}服务已停止${NC}"