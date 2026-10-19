"""HTTP 请求模型：验证、默认值与文档契约。"""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator


class Filters(BaseModel):
    kind: Literal["news", "policy", "price"] | None = None
    minerals: list[str] | None = Field(default=None, max_length=20)
    countries: list[str] | None = Field(default=None, max_length=20)
    since: datetime | None = None
    until: datetime | None = None

    @model_validator(mode="after")
    def validate_interval(self):
        for field in ("since", "until"):
            value = getattr(self, field)
            if value and value.tzinfo is None:
                setattr(self, field, value.replace(tzinfo=ZoneInfo("Asia/Shanghai")))
        if self.since and self.until and self.since > self.until:
            raise ValueError("开始时间不能晚于结束时间")
        return self


class QueryBody(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    filters: Filters | None = None
    as_of: datetime | None = None

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if len(value.strip()) < 2:
            raise ValueError("请输入至少两个字符的问题")
        return value.strip()


class CollectionBody(BaseModel):
    sources: (
        list[Literal["mining", "spglobal", "disr", "regcc", "lme", "mysteel", "gfex"]] | None
    ) = None
    days: int = Field(default=30, ge=1, le=365)
    limit: int = Field(default=200, ge=1, le=1000)
    max_pages: int = Field(default=250, ge=1, le=2000)
