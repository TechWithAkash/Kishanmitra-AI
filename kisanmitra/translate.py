"""Free machine translation (no API key).

Primary: Google Translate's public `gtx` endpoint, which also returns a romanized
version of the output (used to reply in Latin script to users who type Hinglish).
It is an unofficial endpoint and rate-limits (HTTP 429) under load, so:
  * after a 429 it is skipped for a minute (a "circuit breaker"), instead of being hammered;
  * MyMemory (free, 500 characters per request) takes over, with long texts split into pieces.
MyMemory is OFF by default (KISANMITRA_ALLOW_MYMEMORY=1 enables it): in testing it turned
"kal baarish hogi kya" into "the Return of the Irish" and invented a "Pune" in a weather reply.
For farming advice a wrong translation is worse than an honest English answer.
If every allowed service fails, the original text is returned and the caller is told (`ok=False`).
Failures are never cached, so a temporary outage does not stick. Successes are cached in memory and
on disk, so fixed texts (crop advice, templates) keep working after a restart even if Google is blocked.
"""

import hashlib
import json
import logging
import re
import threading
import time

import requests

from kisanmitra.config import settings

log = logging.getLogger("kisanmitra.translate")

GTX_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
GTX_CHUNK = 1800          # characters per gtx request (the URL has a length limit)
MYMEMORY_CHUNK = 450      # MyMemory rejects anything over 500 characters
BREAKER_SECONDS = 60
CACHE_SIZE = 1000

_lock = threading.Lock()
_cache: dict[tuple, str] = {}
_gtx_blocked_until = 0.0
ALLOW_MYMEMORY = settings.allow_mymemory

DISK_MAX_BYTES = 8 * 1024 * 1024
DISK_MAX_TEXT = 4000
_disk: dict[str, str] | None = None   # loaded on first use


def _disk_file():
    return settings.cache_dir / "translations.jsonl"


def _disk_key(key: tuple) -> str:
    return hashlib.sha1(json.dumps(key, ensure_ascii=False).encode("utf-8")).hexdigest()


def _disk_load() -> dict[str, str]:
    global _disk
    if _disk is None:
        _disk = {}
        try:
            for line in _disk_file().read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                    _disk[row["k"]] = row["v"]
                except (ValueError, KeyError):
                    continue  # a half-written last line must not break startup
        except OSError:
            pass
    return _disk


def _disk_save(key: tuple, value: str) -> None:
    if len(key[0]) > DISK_MAX_TEXT:
        return
    k = _disk_key(key)
    disk = _disk_load()
    if disk.get(k) == value:
        return
    disk[k] = value
    try:
        path = _disk_file()
        if path.exists() and path.stat().st_size > DISK_MAX_BYTES:
            return  # the cache stops growing instead of filling the disk
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"k": k, "v": value}, ensure_ascii=False) + "\n")
    except OSError as exc:
        log.warning("could not write translation cache: %s", exc)


class TranslationError(RuntimeError):
    pass


def _hard_cut(text: str, limit: int) -> list[str]:
    """Cut a long run of text at spaces (or exactly at `limit` if there is none)."""
    pieces = []
    while len(text) > limit:
        cut = text.rfind(" ", 0, limit)
        cut = cut if cut > 0 else limit
        pieces.append(text[:cut])
        text = text[cut:].lstrip()
    return pieces + [text]


def split_text(text: str, limit: int) -> list[str]:
    """Cut `text` into pieces of at most `limit` characters, preferring line ends, then sentence ends, then spaces."""
    if len(text) <= limit:
        return [text]
    units: list[str] = []
    for line in text.split("\n"):
        if len(line) <= limit:
            units.append(line)
            continue
        for sentence in re.split(r"(?<=[.!?।])\s+", line):
            units.extend(_hard_cut(sentence, limit) if len(sentence) > limit else [sentence])
    pieces: list[str] = []
    current = ""
    for unit in units:
        joined = f"{current}\n{unit}" if current else unit
        if len(joined) <= limit:
            current = joined
        else:
            if current:
                pieces.append(current)
            current = unit
    if current:
        pieces.append(current)
    return pieces


def _gtx(text: str, source: str, target: str) -> tuple[str, str | None]:
    translated: list[str] = []   # one entry per piece
    romanized: list[str] = []
    for piece in split_text(text, GTX_CHUNK):
        params = {"client": "gtx", "sl": source, "tl": target, "dt": ["t", "rm"], "q": piece}
        resp = requests.get(GTX_URL, params=params, timeout=15)
        if resp.status_code in (429, 403):
            raise TranslationError(f"gtx rate limited (HTTP {resp.status_code})")
        resp.raise_for_status()
        segments: list[str] = []
        rm = None
        for seg in resp.json()[0]:
            if seg[0] is not None:
                segments.append(seg[0])
            elif len(seg) > 2 and isinstance(seg[2], str):
                rm = seg[2]
        translated.append("".join(segments))
        if rm:
            romanized.append(rm)
    return "\n".join(translated), "\n".join(romanized) or None


def _mymemory(text: str, source: str, target: str) -> str:
    out: list[str] = []
    for piece in split_text(text, MYMEMORY_CHUNK):
        params = {"q": piece, "langpair": f"{source}|{target}"}
        if "@" in settings.contact:  # an email raises the free daily quota from 5k to 50k characters
            params["de"] = settings.contact
        resp = requests.get(MYMEMORY_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        # MyMemory reports errors and quota warnings inside an HTTP 200 reply: never show those as a translation.
        if str(data.get("responseStatus")) != "200" or not translated or translated.isupper() and len(translated) > 20:
            raise TranslationError(f"MyMemory refused: {translated[:60]}")
        out.append(translated)
    return "\n".join(out)


def translate_ex(text: str, target: str, source: str = "en", romanize: bool = False) -> tuple[str, bool]:
    """Translate `text`. Returns (translation, ok). When ok is False the original text is returned."""
    global _gtx_blocked_until
    if not text.strip() or source == target:
        return text, True
    key = (text, target, source, romanize)
    with _lock:
        if key in _cache:
            return _cache[key], True
        saved = _disk_load().get(_disk_key(key))
        if saved is not None:
            _cache[key] = saved
            return saved, True

    result: str | None = None
    if time.monotonic() >= _gtx_blocked_until:
        try:
            translated, rm = _gtx(text, source, target)
            result = rm if romanize and rm else translated
        except TranslationError as exc:
            _gtx_blocked_until = time.monotonic() + BREAKER_SECONDS
            log.warning("%s: using MyMemory for the next %ds", exc, BREAKER_SECONDS)
        except (requests.RequestException, ValueError, IndexError, TypeError) as exc:
            log.warning("gtx failed: %s", type(exc).__name__)
    if result is None and ALLOW_MYMEMORY:
        try:
            result = _mymemory(text, "Autodetect" if source == "auto" else source, target)  # MyMemory's name for "auto"
        except (TranslationError, requests.RequestException, ValueError, KeyError) as exc:
            log.warning("MyMemory failed: %s", exc if isinstance(exc, TranslationError) else type(exc).__name__)
    if result is None:
        return text, False

    with _lock:
        if len(_cache) >= CACHE_SIZE:
            _cache.clear()
        _cache[key] = result
        _disk_save(key, result)
    return result, True


def translate(text: str, target: str, source: str = "en", romanize: bool = False) -> str:
    return translate_ex(text, target, source, romanize)[0]
