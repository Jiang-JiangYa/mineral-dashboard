from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, Field, field_validator, model_validator

MINERALS = {
    '铜': ['copper', '铜'], '锌': ['zinc', '锌'], '镍': ['nickel', '镍'],
    '锂': ['lithium', 'spodumene', '锂', '碳酸锂'],
    '铁矿石': ['iron ore', 'iron-ore', '铁矿石', '铁矿'],
    '稀土': ['rare earth', 'rare-earth', '稀土'], '钴': ['cobalt', '钴'],
    '金': ['gold', '黄金', '金矿'], '石墨': ['graphite', '石墨'],
}
COUNTRIES = {
    'AU': ['australia', 'australian', '澳洲', '澳大利亚'],
    'CN': ['china', 'chinese', '中国', '稀土集团'],
    'US': ['united states', '美国', 'u.s.'],
    'CA': ['canada', 'canadian', '加拿大'],
    'CL': ['chile', 'chilean', '智利'], 'ID': ['indonesia', '印尼', '印度尼西亚'],
}


def utcnow():
    return datetime.now(timezone.utc)


def identify(text, vocabulary):
    lowered = text.casefold()
    return [key for key, aliases in vocabulary.items() if any(alias in lowered for alias in aliases)]


class Record(BaseModel):
    kind: Literal['news', 'policy', 'price']
    source: str = Field(min_length=1, max_length=100)
    url: str
    title: str = Field(min_length=3, max_length=1000)
    text: str = Field(min_length=20, max_length=300000)
    published_at: datetime
    fetched_at: datetime = Field(default_factory=utcnow)
    minerals: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    publisher: str = ''
    document_type: str = ''
    is_reference: bool = False
    market: str = ''
    instrument: str = ''
    contract: str = ''
    quote_type: str = ''
    currency: str = ''
    unit: str = ''
    price: Decimal | None = None
    raw_path: str = ''

    @field_validator('url')
    @classmethod
    def valid_url(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('来源必须是无嵌入凭据的 HTTP(S) URL')
        return value

    @field_validator('published_at', 'fetched_at')
    @classmethod
    def aware_dates(cls, value):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @model_validator(mode='after')
    def validate_record(self):
        self.minerals = self.minerals or identify(self.title + ' ' + self.text + ' ' + self.instrument, MINERALS)
        self.countries = self.countries or identify(self.title + ' ' + self.text, COUNTRIES)
        if self.published_at > utcnow():
            raise ValueError('发布日期不能在未来')
        if self.kind == 'price':
            if self.price is None or not self.price.is_finite() or self.price <= 0:
                raise ValueError('价格必须是有限正数')
            if not all((self.market, self.instrument, self.quote_type, self.currency, self.unit)):
                raise ValueError('价格缺少市场、产品、口径、币种或单位')
            if self.market.upper() == 'SHFE' and '锂' in self.minerals:
                raise ValueError('碳酸锂期货属于 GFEX，不能标为 SHFE；请先核实原始价格来源')
        return self
