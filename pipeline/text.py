import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import COUNTRIES, MINERALS

STOPWORDS = set(
    "the a an and to of in for on with is at by from as it be are this that or was were has have its".split()
)
ALIASES = {
    "policy": [
        "policy",
        "policies",
        "strategy",
        "strategic",
        "regulation",
        "regulations",
        "政策",
        "战略",
        "条例",
        "办法",
        "规定",
    ],
    "export": ["export", "exports", "exporting", "出口", "出口管制"],
    "supply": ["supply", "供应", "供应链"],
    "price": ["price", "prices", "价格", "报价", "结算价"],
    "investment": ["investment", "investments", "投资"],
    "recycling": ["recycling", "回收"],
    "processing": ["processing", "加工", "冶炼"],
    "research": ["research", "研发", "科研"],
    "tax": ["tax", "税", "税收"],
}


def clean_text(text):
    text = unicodedata.normalize("NFKC", text).replace("\x00", "")
    return "\n".join(
        re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.splitlines() if line.strip()
    )


def canonical_url(url):
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in ("fbclid", "gclid", "ref")
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            urlencode(sorted(query)),
            "",
        )
    )


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_id(record):
    if record.kind == "price":
        key = "|".join(
            [
                record.source,
                record.market,
                record.instrument,
                record.contract,
                record.published_at.isoformat(),
                record.quote_type,
                record.currency,
                record.unit,
            ]
        )
    else:
        key = record.source + "|" + canonical_url(record.url)
    return digest(key)


def chunks(text, size=900, overlap=120):
    if size <= overlap:
        raise ValueError("chunk size must exceed overlap")
    result, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(
                text.rfind("\n", start + size // 2, end), text.rfind("。", start + size // 2, end)
            )
            if boundary > start:
                end = boundary + 1
        result.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return result


def tokens(text):
    lowered = text.casefold()
    result = [
        w for w in re.findall(r"[a-z][a-z0-9_-]+|\d+(?:\.\d+)?", lowered) if w not in STOPWORDS
    ]
    for sequence in re.findall(r"[\u4e00-\u9fff]+", lowered):
        result.extend(sequence[i : i + 2] for i in range(len(sequence) - 1))
    for key, aliases in {**MINERALS, **COUNTRIES, **ALIASES}.items():
        if any(alias in lowered for alias in aliases):
            result.extend([key, key, key])
    return result
