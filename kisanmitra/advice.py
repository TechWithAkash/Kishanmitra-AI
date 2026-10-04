"""Crop-problem knowledge base lookup (crop × symptom → advice)."""

import json
from functools import lru_cache

from kisanmitra import DATA_DIR


@lru_cache(maxsize=1)
def _kb() -> list[dict]:
    with open(DATA_DIR / "advice.json", encoding="utf-8") as f:
        return json.load(f)


def find_advice(crop: str | None, symptom: str | None) -> dict | None:
    """Exact crop+symptom match first, then the generic ("*") entry for the symptom."""
    if not symptom:
        return None
    for crop_key in (crop, "*"):
        for entry in _kb():
            if entry["crop"] == crop_key and entry["symptom"] == symptom:
                return entry
    return None
