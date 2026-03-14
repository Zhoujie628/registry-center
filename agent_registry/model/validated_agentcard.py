import re

from a2a.types import AgentCard
from pydantic import field_validator, model_validator, HttpUrl

_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')


class ValidatedAgentCard(AgentCard):
    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """验证名称仅包含字母、数字和下划线"""
        if not _NAME_PATTERN.fullmatch(v):
            raise ValueError('Name must contain only alphanumeric characters and underscores.')
        return v

    @model_validator(mode='after')
    def validate_provider(self):
        if self.provider and hasattr(self.provider, 'url') and self.provider.url:
            try:
                # 如果 url 不符合标准，HttpUrl 会抛出 ValidationError
                HttpUrl(self.provider.url)
            except Exception:
                raise ValueError('Provider URL must be a valid web URL.')
        return self
