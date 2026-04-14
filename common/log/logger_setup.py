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

import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger

from common.util.config_util import get_root_path

root_path = get_root_path()
_LOG_DIR = Path(root_path) / "log"
_LOG_DIR.mkdir(exist_ok=True)
os.chmod(_LOG_DIR, 0o700)

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: ^8}</level> | "
    "process [<cyan>{process}</cyan>]:<cyan>{thread}</cyan> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def add_module_logger(module_prefix: str):
    """
    Configures logging for a module with console and file outputs.

    Args:
        module_prefix (str): Prefix for log file names (e.g., "module_name").
    """

    def compress_and_set_permission(source_file):
        """
        自定义压缩函数
        source_file: 需要压缩的日志文件路径
        返回值: 压缩后的文件路径（或 None）
        """
        # 构建压缩文件名
        zip_file = Path(str(source_file) + ".zip")

        try:
            # 执行压缩
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(source_file, arcname=Path(source_file).name)

            # 压缩完成后立即修改权限
            os.chmod(zip_file, 0o440)

            # 可选：删除原始日志文件
            os.remove(source_file)

            return zip_file
        except Exception as e:
            logger.error(f"压缩或设置权限失败: {e}")
            return None

    logger.configure(extra={"request_id": ''})
    logger.remove()
    old_mask = os.umask(0o027)
    # Console output
    try:
        logger.add(
            sys.stdout,
            format=LOG_FORMAT,
            level="INFO",
            backtrace=False,
            colorize=True,
        )

        # Regular log file
        logger.add(
            _LOG_DIR / f"{module_prefix}_log_{{time:YYYY-MM-DD}}.log",
            format=LOG_FORMAT,
            level="INFO",
            rotation=lambda message, file: (
                    os.stat(file.name).st_size > 10 * 1024 * 1024
                    or datetime.now(tz=timezone.utc).date() != datetime.fromtimestamp(
                os.path.getctime(file.name)).date()
            ),
            retention="30 days",
            encoding="utf-8",
            compression=compress_and_set_permission,
            enqueue=True,
        )

        # Error log file
        logger.add(
            _LOG_DIR / f"{module_prefix}_error_{{time:YYYY-MM-DD}}.log",
            format=LOG_FORMAT,
            level="ERROR",
            rotation=lambda message, file: (
                    os.stat(file.name).st_size > 10 * 1024 * 1024
                    or datetime.now(tz=timezone.utc).date() != datetime.fromtimestamp(
                os.path.getctime(file.name)).date()
            ),
            retention="30 days",
            encoding="utf-8",
            compression=compress_and_set_permission,
            enqueue=True,
        )
    finally:
        os.umask(old_mask)

