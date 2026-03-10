from pathlib import Path
from loguru import logger

_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {message}"


def add_module_logger(module_prefix: str):
    """
    为指定的顶层模块添加独立的日志文件，按日轮转。
    文件名示例：agent_registry_2025-03-06.log
    """
    logger.add(
        _LOG_DIR / f"{module_prefix}_{{time:YYYY-MM-DD}}.log",
        format=LOG_FORMAT,
        level="INFO",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )
