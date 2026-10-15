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


FUZZY_MIN_LENGTH = 5      # shorter words must match exactly: "worm" and "word" are one letter apart


def edit_distance(a: str, b: str) -> int:
    """Number of single-letter changes (insert, delete, replace, swap neighbours) to turn `a` into `b`."""
    prev2, prev = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            best = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            if prev2 is not None and i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                best = min(best, prev2[j - 2] + 1)   # swapped neighbours: "teh" -> "the"
            cur.append(best)
        prev2, prev = prev, cur
    return prev[-1]


@lru_cache(maxsize=2)
def _spelling_vocab(kind: str) -> dict[str, str]:
    """Single Latin-script words we know for crops / symptoms, mapped to what they mean."""
    table = {k: v["variants"] for k, v in crops().items()} if kind == "crop" else _load("symptoms.json")
    return {
        variant.lower(): canon
        for canon, variants in table.items()
        for variant in variants
        if variant.isascii() and variant.isalpha() and len(variant) >= FUZZY_MIN_LENGTH
    }


def sound_key(word: str) -> str:
    """Hindi written in English letters has no fixed spelling: aloo / aaloo / aalu / alu are one word.
    This folds the usual long-vowel variants together (aa->a, ee->i, oo->u, ii->i, uu->u).
    It deliberately does NOT fold everything: "root" becomes "rut", which is not the symptom word "rot"."""
    for long, short in (("aa", "a"), ("ee", "i"), ("oo", "u"), ("ii", "i"), ("uu", "u")):
        word = word.replace(long, short)
    return word


@lru_cache(maxsize=2)
def _sound_vocab(kind: str) -> dict[str, str]:
    table = {k: v["variants"] for k, v in crops().items()} if kind == "crop" else _load("symptoms.json")
    return {
        sound_key(v.lower()): canon
        for canon, variants in table.items()
        for v in variants
        if v.isascii() and v.isalpha() and len(v) >= 3
    }


def _fuzzy(text: str, kind: str) -> str | None:
    """Understand misspelled words ("yello leaves", "tomatoo", "cotten", "aaloo"). Only crops and symptoms: never places.

    1. Same sound: aaloo = aloo (see sound_key).
    2. One slip is allowed in words up to 7 letters, two in longer words, and the first letter must be right.
       "weather" is 3 edits from "wheat" and "word" is only 4 letters, so neither is mistaken for a crop or symptom.
    """
    vocab, sounds = _spelling_vocab(kind), _sound_vocab(kind)
    for word in re.findall(r"[a-z]{3,}", text):
        if sound_key(word) in sounds:
            return sounds[sound_key(word)]
        if len(word) < FUZZY_MIN_LENGTH:
            continue
        allowed = 1 if len(word) <= 7 else 2
        for known, meaning in vocab.items():
            if known[0] == word[0] and abs(len(known) - len(word)) <= allowed and edit_distance(word, known) <= allowed:
                return meaning
    return None


def explain_entities(text: str) -> list[dict]:
    """Where each entity was found in `text`, for highlighting: [{type, value, text, start, end, how}]."""
    lower = text.lower()
    found: list[dict] = []
    for kind, patterns in _patterns().items():
        best = None
        for pattern, canon in patterns:
            m = pattern.search(lower)
            if m and (best is None or m.start() < best[0].start()):
                best = (m, canon)
        if best:
            m, canon = best
            found.append({"type": kind, "value": canon, "text": text[m.start():m.end()], "start": m.start(), "end": m.end(), "how": "keyword list"})
            continue
        if kind in ("crop", "symptom"):  # misspelled words
            for m in re.finditer(r"[a-z]{3,}", lower):
                value = _fuzzy(m.group(0), kind)
                if value:
                    found.append({"type": kind, "value": value, "text": text[m.start():m.end()], "start": m.start(), "end": m.end(), "how": "spelling correction"})
                    break
    return sorted(found, key=lambda e: e["start"])


def extract_entities(text: str) -> Entities:
    text = text.lower()
    p = _patterns()
    crop = _first_match(text, p["crop"])
    symptom = _first_match(text, p["symptom"])
    return Entities(
        crop=crop or _fuzzy(text, "crop"),
        symptom=symptom or _fuzzy(text, "symptom"),
        location=_first_match(text, p["location"]),
    )
