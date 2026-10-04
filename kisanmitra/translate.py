"""Free machine translation (no API key).

Primary: Google Translate's public `gtx` endpoint, which also returns a romanized
version of the output (used to reply in Latin script to users who type Hinglish).
Fallback: MyMemory free API. If both fail, the original text is returned unchanged.
"""

from functools import lru_cache

import requests

GTX_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"


def _gtx(text: str, source: str, target: str) -> tuple[str, str | None]:
    params = {"client": "gtx", "sl": source, "tl": target, "dt": ["t", "rm"], "q": text}
    resp = requests.get(GTX_URL, params=params, timeout=15)
    resp.raise_for_status()
    translated, romanized = [], None
    for seg in resp.json()[0]:
        if seg[0] is not None:
            translated.append(seg[0])
        elif len(seg) > 2 and isinstance(seg[2], str):
            romanized = seg[2]
    return "".join(translated), romanized


def _mymemory(text: str, source: str, target: str) -> str:
    resp = requests.get(MYMEMORY_URL, params={"q": text, "langpair": f"{source}|{target}"}, timeout=15)
    resp.raise_for_status()
    return resp.json()["responseData"]["translatedText"]


@lru_cache(maxsize=512)
def translate(text: str, target: str, source: str = "en", romanize: bool = False) -> str:
    if not text.strip() or source == target:
        return text
    try:
        translated, romanized = _gtx(text, source, target)
        return romanized if romanize and romanized else translated
    except (requests.RequestException, ValueError, IndexError, TypeError):
        pass
    try:
        return _mymemory(text, "en" if source == "auto" else source, target)
    except (requests.RequestException, ValueError, KeyError):
        return text
