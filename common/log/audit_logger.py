# audit_logger.py
import os
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any
from loguru import logger

from common.util.config_util import get_root_path, load_configs

# 文件权限：600 -> 属主读写，其他无权限
FILE_PERMISSION_MODE = 0o600


class LogLevel:
    DANGER = "Critical"
    MINOR = "General"
    INFO = "Informational"


class OperationName:
    START_SERVICE = "Start Service"
    REGISTER_AGENT = "Register Agent"


class OperatorObject:
    SERVICE = "Service"
    AGENT = "Agent"


class OperationResult:
    SUCCESS = "Success"
    FAILURE = "Failure"


class AuditLogger:
    """
    安全审计日志 SDK
    支持 UTC 时间、文件滚动、绕接删除、权限控制
    """

    def __init__(self):
        self.config = self._load_config()
        self.max_size = int(self.config.get("audit_log_max_file_size_mb", 5)) * 1024 * 1024  # 转为字节
        self.backup_count = int(self.config.get("audit_log_backup_count", 5)) - 1
        self.log_file = os.path.join(get_root_path(), "log", "audit", "audit.log")
        self.lock = threading.Lock()

        # 确保日志目录存在
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    @staticmethod
    def _load_config() -> Dict[str, Any]:
        """加载配置文件，若不存在则创建默认配置"""
        root_path = get_root_path()
        log_config = {}
        log_config_path = os.path.join(root_path, "etc", "conf", "log_config.conf")
        if os.path.exists(log_config_path):
            load_configs(log_config_path, log_config)
        return log_config

    def audit(self,
              operation_name: str,
              level: str,
              result: str,
              object_name: str,
              details: Dict[str, Any] = None,
              client_ip: str = "",
              user_name: str = ""):
        """
        记录审计日志
        :param operation_name: 操作名称，如“启动服务”
        :param level: 级别：danger、normal、info
        :param result: 成功/失败
        :param object_name: 操作对象，如“Agent”
        :param details: 补充信息
        :param client_ip: 客户端IP，REST接口使用
        :param user_name: 用户名，命令行使用
        """
        log_entry = {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "clientIP": client_ip,
            "userName": user_name,
            "level": level,
            "operationName": operation_name,
            "object": object_name,
            "result": result,
            "details": details or {}
        }
        self._write_log(log_entry)

    def _get_file_size(self) -> int:
        """获取当前日志文件大小，若不存在返回0"""
        return os.path.getsize(self.log_file) if os.path.exists(self.log_file) else 0

    def _rotate_logs(self):
        """安全的日志滚动，避免卡死"""
        if self._get_file_size() < self.max_size:
            return

        # 1. 先删除最旧的文件（.backup_count + 1）
        oldest = f"{self.log_file}.{self.backup_count + 1}"
        if os.path.exists(oldest):
            try:
                os.remove(oldest)
            except Exception as e:
                logger.error(f"Warning: failed to remove {oldest}: {e}")  # 不要 raise，避免阻塞日志

        # 2. 从高到低重命名：.4 -> .5, .3 -> .4, ..., .1 -> .2
        for i in range(self.backup_count, 0, -1):
            src = f"{self.log_file}.{i}"
            dst = f"{self.log_file}.{i + 1}"
            if os.path.exists(src):
                try:
                    os.rename(src, dst)
                except Exception as e:
                    logger.error(f"Warning: failed to rename {src} to {dst}: {e}")

        # 3. 将当前主日志重命名为 .1
        if os.path.exists(self.log_file):
            try:
                os.rename(self.log_file, f"{self.log_file}.1")
            except Exception as e:
                logger.error(f"Warning: failed to rename {self.log_file} to {self.log_file}.1: {e}")
                return  # 如果主文件重命名失败，不要继续

        # 4. 创建新日志文件
        try:
            open(self.log_file, 'w').close()
            os.chmod(self.log_file, FILE_PERMISSION_MODE)
        except Exception as e:
            logger.error(f"Error: failed to create new log file: {e}")

    def _write_log(self, log_entry: Dict[str, Any]):
        """写入单条日志，线程安全"""
        with self.lock:
            self._rotate_logs()  # 滚动判断
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            # 确保权限（尤其新创建时）
            os.chmod(self.log_file, FILE_PERMISSION_MODE)


audit_logger = AuditLogger()
