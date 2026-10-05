"""Mandi prices from data.gov.in (Agmarknet daily prices dataset). Free API.

Get your own free key at https://data.gov.in (set DATA_GOV_API_KEY). Without one the
public sample key is used, which is often rate-limited.

Resilience: every successful answer is saved to disk. If the API is down later, the last
saved prices (up to 48 hours old) are shown and clearly labelled as saved. Only if there is
nothing saved does the app fall back to the built-in demo sample.
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field

import requests

from kisanmitra import DATA_DIR
from kisanmitra.config import redact, settings

log = logging.getLogger("kisanmitra.mandi")

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
CACHE_MAX_AGE = 48 * 3600
TIMEOUT = 8

_lock = threading.Lock()


@dataclass
class PriceResult:
    records: list[dict] = field(default_factory=list)
    scope: str = "india"        # "district" | "state" | "india": how closely records match the location
    source: str = "live"        # "live" | "cached" | "sample"
    error: str | None = None
    fetched_at: float | None = None   # unix time the prices were downloaded (live: now; cached: earlier)


# ---------------------------------------------------------------- disk cache

def _cache_file():
    return settings.cache_dir / "mandi.json"


def _cache_key(commodity: str, state: str | None) -> str:
    return f"{commodity.lower()}|{(state or '').lower()}"


def _cache_load() -> dict:
    try:
        return json.loads(_cache_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _cache_save(commodity: str, state: str | None, records: list[dict]) -> None:
    try:
        with _lock:
            data = _cache_load()
            data[_cache_key(commodity, state)] = {"ts": time.time(), "records": records}
            _cache_file().parent.mkdir(parents=True, exist_ok=True)
            tmp = _cache_file().with_suffix(".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.replace(_cache_file())
    except OSError as exc:  # a read-only disk must never break an answer
        log.warning("could not write mandi cache: %s", exc)


def _cache_get(commodity: str, state: str | None) -> tuple[list[dict], float] | None:
    for key in (_cache_key(commodity, state), _cache_key(commodity, None)):
        entry = _cache_load().get(key)
        if entry and time.time() - entry["ts"] <= CACHE_MAX_AGE:
            return entry["records"], entry["ts"]
    return None


# ---------------------------------------------------------------- sources

def _fetch_live(commodity: str, state: str | None) -> list[dict]:
    params = {
        "api-key": os.environ.get("DATA_GOV_API_KEY", SAMPLE_KEY),
        "format": "json",
        "limit": 100,
        "filters[commodity]": commodity,
    }
    if state:
        params["filters[state.keyword]"] = state
    resp = requests.get(URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("records", [])


def _load_sample(commodity: str) -> list[dict]:
    with open(DATA_DIR / "mandi_sample.json", encoding="utf-8") as f:
        data = json.load(f)
    return [r for r in data["records"] if r["commodity"].lower() == commodity.lower()]


def _narrow(records: list[dict], district: str | None, state: str | None) -> tuple[list[dict], str]:
    """Filter client-side too, so results are right even if the API ignores a filter."""
    if district:
        hits = [r for r in records if r.get("district", "").lower() == district.lower()]
        if hits:
            return hits, "district"
    if state:
        hits = [r for r in records if r.get("state", "").lower() == state.lower()]
        if hits:
            return hits, "state"
    return records, "india"


def get_prices(commodity: str, district: str | None = None, state: str | None = None) -> PriceResult:
    error = None
    fetched_at: float | None = None
    try:
        records = _fetch_live(commodity, state) if state else []
        if not records:
            records = _fetch_live(commodity, None)
            state_for_cache = None
        else:
            state_for_cache = state
        source, fetched_at = "live", time.time()
        if records:
            _cache_save(commodity, state_for_cache, records)
    except (requests.RequestException, ValueError) as exc:
        error = redact(f"{type(exc).__name__}: {exc}")  # the URL in the message contains the API key
        log.warning("mandi API failed: %s", error)
        saved = _cache_get(commodity, state)
        if saved:
            (records, fetched_at), source = saved, "cached"
        else:
            records, source = _load_sample(commodity), "sample"

    records = [r for r in records if r.get("commodity", "").lower() == commodity.lower()] or records
    records, scope = _narrow(records, district, state)
    records.sort(key=lambda r: float(r.get("modal_price") or 0), reverse=True)
    return PriceResult(records=records[:5], scope=scope, source=source, error=error, fetched_at=fetched_at)
