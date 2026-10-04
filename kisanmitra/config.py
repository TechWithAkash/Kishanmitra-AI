"""Runtime settings, all overridable with environment variables (see .env.example)."""

import os
from dataclasses import dataclass
from pathlib import Path


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _flag(name: str, default: bool) -> bool:
    return os.environ.get(name, "1" if default else "0").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    cache_dir: Path
    cors_origins: tuple[str, ...]
    rate_limit_per_min: int          # normal endpoints, per client IP
    heavy_rate_limit_per_min: int    # voice / photo / speech endpoints, per client IP
    max_upload_mb: int
    max_text_chars: int
    trust_proxy: bool                # read the client IP from X-Forwarded-For (API sits behind the web proxy)
    log_level: str
    contact: str                     # sent in the User-Agent of free public APIs (OpenStreetMap asks for this)


def load_settings() -> Settings:
    root = Path(__file__).resolve().parent.parent
    origins = os.environ.get("KISANMITRA_CORS_ORIGINS", "")
    return Settings(
        cache_dir=Path(os.environ.get("KISANMITRA_CACHE_DIR", root / ".cache")),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        rate_limit_per_min=_int("KISANMITRA_RATE_LIMIT", 120),
        heavy_rate_limit_per_min=_int("KISANMITRA_HEAVY_RATE_LIMIT", 30),
        max_upload_mb=_int("KISANMITRA_MAX_UPLOAD_MB", 12),
        max_text_chars=_int("KISANMITRA_MAX_TEXT_CHARS", 1000),
        trust_proxy=_flag("KISANMITRA_TRUST_PROXY", True),
        log_level=os.environ.get("KISANMITRA_LOG_LEVEL", "INFO").upper(),
        contact=os.environ.get("KISANMITRA_CONTACT", "academic project"),
    )


settings = load_settings()
