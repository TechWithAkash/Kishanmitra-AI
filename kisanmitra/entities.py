"""Step 3 — entity extraction with multilingual keyword lists (gazetteers).

Latin-script variants match whole words; Devanagari variants match as substrings so
inflected forms still hit (कांद्याचा → कांद्या, पुण्यात → पुण्यात, नाशिकमध्ये → नाशिक).
"""

import json
import re
from dataclasses import dataclass, asdict
from functools import lru_cache

from kisanmitra import DATA_DIR


@dataclass
class Entities:
    crop: str | None = None       # canonical id, e.g. "onion"
    symptom: str | None = None    # canonical id, e.g. "yellowing"
    location: str | None = None   # canonical name, e.g. "Nashik"

    def as_dict(self) -> dict:
        return asdict(self)


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def crops() -> dict:
    return _load("crops.json")


@lru_cache(maxsize=1)
def locations() -> dict:
    return _load("locations.json")


@lru_cache(maxsize=1)
def _patterns() -> dict[str, list[tuple[re.Pattern, str]]]:
    tables = {
        "crop": {k: v["variants"] for k, v in crops().items()},
        "symptom": _load("symptoms.json"),
        "location": {k: v["variants"] for k, v in locations().items()},
    }
    patterns = {}
    for kind, table in tables.items():
        items = [(variant, canon) for canon, variants in table.items() for variant in variants]
        items.sort(key=lambda x: -len(x[0]))  # longest first
        patterns[kind] = [
            (re.compile(rf"\b{re.escape(v)}\b" if v.isascii() else re.escape(v)), canon)
            for v, canon in items
        ]
    return patterns


def _first_match(text: str, patterns: list[tuple[re.Pattern, str]]) -> str | None:
    best = None  # (position, canonical)
    for pattern, canon in patterns:
        m = pattern.search(text)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), canon)
    return best[1] if best else None


@lru_cache(maxsize=1)
def known_words() -> frozenset[str]:
    """Every Latin-script word the keyword lists already understand (crops, symptoms, cities)."""
    words: set[str] = set()
    tables = [v["variants"] for v in crops().values()] + list(_load("symptoms.json").values())
    tables += [v["variants"] for v in locations().values()]
    for variants in tables:
        for variant in variants:
            words.update(re.findall(r"[a-z]+", variant.lower()))
    return frozenset(words)


def extract_entities(text: str) -> Entities:
    text = text.lower()
    p = _patterns()
    return Entities(
        crop=_first_match(text, p["crop"]),
        symptom=_first_match(text, p["symptom"]),
        location=_first_match(text, p["location"]),
    )
