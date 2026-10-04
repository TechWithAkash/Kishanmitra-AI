"""Step 1 — language + script detection.

Rule-based on purpose: generic detectors (langdetect, fastText) mislabel romanized
Hindi ("mera tamatar peela hai") and short Hindi-vs-Marathi Devanagari text.
"""

import re
from dataclasses import dataclass

# Unicode block → language for Indic scripts that map to (mostly) one language.
SCRIPT_RANGES = [
    ((0x0600, 0x06FF), "ur"),
    ((0x0900, 0x097F), "devanagari"),
    ((0x0980, 0x09FF), "bn"),
    ((0x0A00, 0x0A7F), "pa"),
    ((0x0A80, 0x0AFF), "gu"),
    ((0x0B00, 0x0B7F), "or"),
    ((0x0B80, 0x0BFF), "ta"),
    ((0x0C00, 0x0C7F), "te"),
    ((0x0C80, 0x0CFF), "kn"),
    ((0x0D00, 0x0D7F), "ml"),
]

MARATHI_WORDS = {
    "आहे", "आहेत", "काय", "माझ्या", "माझा", "माझी", "माझे", "मला", "करू", "करावे", "करावा",
    "नाही", "कसे", "कसा", "किती", "आणि", "मध्ये", "सांगा", "आजचा", "आजचे", "उद्या", "पाऊस",
    "झाली", "झाले", "होत", "पडेल", "येईल", "तुम्ही", "करा", "पडली", "पडत", "आली", "टाकावा",
}
MARATHI_SUFFIXES = ("च्या", "चा", "ची", "मध्ये", "ात")
HINDI_WORDS = {
    "है", "हैं", "का", "की", "के", "में", "क्या", "रहा", "रहे", "रही", "करूं", "करें", "हो",
    "कैसा", "कितना", "बताओ", "मेरे", "मेरा", "मेरी", "गया", "गई", "गए", "होगी", "दो", "कौन",
}

HINGLISH_WORDS = {
    "hai", "hain", "ka", "ki", "ke", "kya", "mera", "meri", "mere", "me", "mein", "ho", "raha",
    "rahe", "rahi", "kare", "karu", "karen", "karo", "kaise", "kaisa", "kab", "kitna", "kitne",
    "nahi", "aur", "bhav", "batao", "aaj", "kal", "hogi", "hoga", "lag", "gaya", "gayi", "gaye",
    "ko", "se", "par", "bhi", "dawai", "fasal", "mausam", "barish", "baarish", "paudha", "patte",
    "keede", "namaste", "dhanyavad", "kaun", "tum", "aap", "yojana", "agle", "jankari", "daam",
    "tamatar", "pyaj", "pyaz", "gehu", "aloo", "kapas", "mirchi", "dhan", "chal", "bik", "rog",
}
MARATHI_ROMAN_WORDS = {"aahe", "ahe", "kay", "majha", "mazha", "mala", "kasa", "kiti", "udya", "paus", "sanga"}
ENGLISH_WORDS = {
    "the", "is", "what", "my", "in", "of", "to", "for", "how", "will", "are", "there", "on",
    "which", "should", "i", "today", "this", "it", "and", "price", "weather", "rain", "leaves",
    "plant", "plants", "crop", "do", "you", "can", "who", "tell", "about", "with", "have",
}

WORD_RE = re.compile(r"[\wऀ-ൿ]+")


@dataclass
class LangResult:
    lang: str      # ISO code: hi, mr, en, te, ...
    script: str    # "native" or "latin"


def _script_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        if ch.isascii() and ch.isalpha():
            counts["latin"] = counts.get("latin", 0) + 1
            continue
        for (lo, hi), name in SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[name] = counts.get(name, 0) + 1
                break
    return counts


def _devanagari_lang(words: list[str]) -> str:
    mr = sum(w in MARATHI_WORDS for w in words)
    mr += sum(w.endswith(MARATHI_SUFFIXES) and w not in HINDI_WORDS for w in words) * 0.5
    hi = sum(w in HINDI_WORDS for w in words)
    return "mr" if mr > hi else "hi"


def _latin_lang(words: list[str]) -> str:
    hi = sum(w in HINGLISH_WORDS for w in words)
    mr = sum(w in MARATHI_ROMAN_WORDS for w in words)
    en = sum(w in ENGLISH_WORDS for w in words)
    if max(hi, mr) > en:
        return "mr" if mr > hi else "hi"
    return "en"


def detect_language(text: str) -> LangResult:
    counts = _script_counts(text)
    if not counts:
        return LangResult("en", "latin")
    script = max(counts, key=counts.get)
    words = WORD_RE.findall(text.lower())
    if script == "latin":
        lang = _latin_lang(words)
        return LangResult(lang, "latin" if lang != "en" else "native")
    if script == "devanagari":
        return LangResult(_devanagari_lang(words), "native")
    return LangResult(script, "native")
