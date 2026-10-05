"""Runtime settings, all overridable with environment variables (see .env.example)."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> None:
    """Load KEY=value lines from the project's .env file. Variables already set in the real environment win."""
    from dotenv import load_dotenv

    load_dotenv(path, override=False)


load_env()  # must run before the settings below (and before any module reads an API key)

SECRET_VARS = ("OPENWEATHER_API_KEY", "DATA_GOV_API_KEY")
_SECRET_PARAMS = re.compile(r"(appid|api-key|apikey|key|token)=[^&\s'\"]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Remove API keys from text. Error messages from the `requests` library include the full URL,
    query string and all, so anything that is logged or sent to a browser must pass through this."""
    for name in SECRET_VARS:
        value = os.environ.get(name, "").strip()
        if len(value) >= 8:
            text = text.replace(value, "***")
    return _SECRET_PARAMS.sub(lambda m: f"{m.group(1)}=***", text)


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
    tts_rate: str                    # speaking speed of the neural voice, e.g. "-8%" (a little slower = clearer)
    allow_mymemory: bool             # use MyMemory when Google Translate fails (its quality is poor: off by default)
    contact: str                     # sent in the User-Agent of free public APIs (OpenStreetMap asks for this)


def load_settings() -> Settings:
    root = ROOT
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
        tts_rate=os.environ.get("KISANMITRA_TTS_RATE", "-8%"),
        allow_mymemory=_flag("KISANMITRA_ALLOW_MYMEMORY", False),
        contact=os.environ.get("KISANMITRA_CONTACT", "academic project"),
    )


settings = load_settings()
