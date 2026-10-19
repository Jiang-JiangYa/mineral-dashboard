import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", str(ROOT / "data"))))
    embedding_backend: str = field(default_factory=lambda: os.getenv("EMBEDDING_BACKEND", "hash"))
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    )
    request_timeout: float = field(
        default_factory=lambda: float(os.getenv("REQUEST_TIMEOUT", "15"))
    )
    request_interval: float = field(
        default_factory=lambda: float(os.getenv("REQUEST_INTERVAL", "1"))
    )
    http_retries: int = field(default_factory=lambda: int(os.getenv("HTTP_RETRIES", "2")))

    def __post_init__(self):
        self.data_dir = Path(self.data_dir)
        if not self.data_dir.is_absolute():
            self.data_dir = ROOT / self.data_dir
        if not math.isfinite(self.request_timeout) or self.request_timeout <= 0:
            raise ValueError("REQUEST_TIMEOUT 必须是有限正数")
        if not math.isfinite(self.request_interval) or self.request_interval < 0:
            raise ValueError("REQUEST_INTERVAL 必须是有限非负数")
        if not 0 <= self.http_retries <= 5:
            raise ValueError("HTTP_RETRIES 必须在 0 到 5 之间")


def csv_env(key, default=""):
    return [value.strip() for value in os.getenv(key, default).split(",") if value.strip()]
