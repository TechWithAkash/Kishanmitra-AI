"""Where is the farmer? Place search, GPS → place, and place names found inside a question.

All free, no API key:
  * Open-Meteo geocoding  — search any village / town / district in India by name
  * OpenStreetMap Nominatim — reverse geocoding (GPS coordinates → village, district, state).
    Its usage policy requires a descriptive User-Agent and at most 1 request per second,
    so calls are serialised and cached.
"""

import re
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass, replace
from functools import lru_cache

import requests

from kisanmitra.config import settings

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
TIMEOUT = 8

# Agmarknet (mandi price data) spells a few states differently from OpenStreetMap.
AGMARKNET_STATES = {
    "Delhi": "NCT of Delhi",
    "Uttarakhand": "Uttrakhand",
    "Andaman and Nicobar Islands": "Andaman and Nicobar",
    "Jammu and Kashmir": "Jammu and Kashmir",
    "Dadra and Nagar Haveli and Daman and Diu": "Dadra and Nagar Haveli",
}

# Words that are never place names, so they are not sent to the geocoder.
NOT_PLACES = {
    "weather", "forecast", "tomorrow", "today", "tonight", "week", "rain", "rainy", "price", "prices", "rate",
    "rates", "market", "mandi", "temperature", "next", "days", "going", "expected", "this", "that", "will",
    "there", "what", "when", "where", "which", "about", "please", "tell", "show", "much", "cost", "selling",
    "sell", "farm", "field", "crop", "crops", "plant", "plants", "leaves", "leaf", "good", "time", "spray",
    "spraying", "irrigation", "wind", "hot", "cold", "humid", "sunny", "cloudy", "storm", "thunder", "area",
    "village", "district", "city", "town", "near", "nearby", "around", "here", "morning", "evening", "night",
    "hello", "thanks", "thank", "help", "need", "want", "know", "give", "check", "latest", "current", "right",
    "mausam", "barish", "baarish", "bhav", "daam", "kitna", "kitne", "batao", "aaj", "kal", "agle",
}


@dataclass(frozen=True)
class Place:
    name: str
    lat: float | None = None
    lon: float | None = None
    state: str | None = None      # e.g. "Maharashtra"
    district: str | None = None   # e.g. "Nashik"
    source: str = "search"        # "gps" | "search" | "query" | "saved"

    def label(self) -> str:
        parts: list[str] = []
        for p in (self.name, self.district, self.state):
            if p and p.lower() not in (x.lower() for x in parts):
                parts.append(p)
        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {**asdict(self), "label": self.label()}

    @property
    def mandi_state(self) -> str | None:
        return AGMARKNET_STATES.get(self.state, self.state) if self.state else None


def fold(text: str) -> str:
    """Lower-case, accent-free, letters/digits only: 'Satānā' → 'satana'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in decomposed if not unicodedata.combining(c)).lower())


# ---------------------------------------------------------------- search

@lru_cache(maxsize=1024)
def _search(query: str, language: str, count: int) -> tuple[Place, ...]:
    resp = requests.get(
        GEOCODE_URL,
        params={"name": query, "count": count, "countryCode": "IN", "language": language},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    seen: set[str] = set()
    out: list[Place] = []
    for r in resp.json().get("results") or []:
        p = Place(r["name"], r["latitude"], r["longitude"], r.get("admin1"), r.get("admin2"), "search")
        if p.label() not in seen:
            seen.add(p.label())
            out.append(p)
    return tuple(out)


def search(query: str, limit: int = 6, language: str = "en") -> list[Place]:
    """Find places in India by (partial) name. Returns [] when the service is unreachable."""
    query = query.strip()
    if len(query) < 2:
        return []
    try:
        return list(_search(query, language, limit))
    except (requests.RequestException, ValueError, KeyError):
        return []


# ---------------------------------------------------------------- reverse (GPS)

_nominatim_lock = threading.Lock()
_nominatim_last = 0.0


def _clean_district(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+(District|Subdistrict|Taluka|Tehsil)$", "", value, flags=re.I).strip() or None


@lru_cache(maxsize=2048)
def _reverse(lat: float, lon: float) -> Place | None:
    global _nominatim_last
    with _nominatim_lock:  # Nominatim policy: max 1 request/second
        wait = 1.1 - (time.monotonic() - _nominatim_last)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = requests.get(
                REVERSE_URL,
                params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 14, "addressdetails": 1, "accept-language": "en"},
                headers={"User-Agent": f"KisanMitra/1.0 ({settings.contact})"},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError):
            return None
        finally:
            _nominatim_last = time.monotonic()

    addr = data.get("address") or {}
    name = next(
        (addr[k] for k in ("village", "hamlet", "town", "suburb", "city_district", "city", "municipality", "county") if addr.get(k)),
        None,
    )
    if not name:
        return None
    district = _clean_district(addr.get("state_district") or addr.get("county") or addr.get("city"))
    return Place(name, lat, lon, addr.get("state"), district, "gps")


def reverse(lat: float, lon: float) -> Place:
    """GPS coordinates → the nearest village/town with its district and state."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Invalid coordinates")
    place = _reverse(round(lat, 3), round(lon, 3))
    # If the lookup service is unreachable we still keep the coordinates: weather needs only those.
    return replace(place, lat=lat, lon=lon) if place else Place(f"{lat:.2f}, {lon:.2f}", lat, lon, None, None, "gps")


# ---------------------------------------------------------------- from a question

def from_gazetteer(name: str) -> Place:
    """A place from our built-in list of ~40 cities (state is known; coordinates are looked up lazily)."""
    from kisanmitra.entities import locations

    entry = locations().get(name, {})
    return Place(name, None, None, entry.get("state"), name, "query")


def ensure_coordinates(place: Place) -> Place | None:
    """Fill in latitude/longitude for places that only have a name."""
    if place.lat is not None and place.lon is not None:
        return place
    hits = search(place.name, limit=5)
    if place.state:
        hits = [h for h in hits if h.state == place.state] or hits
    return replace(place, lat=hits[0].lat, lon=hits[0].lon, district=place.district or hits[0].district) if hits else None


def guess_from_text(text: str, ignore: set[str]) -> Place | None:
    """Find a village/town name in free text (e.g. 'will it rain in Satana tomorrow').

    Each unfamiliar word is looked up; a place is accepted only if its name matches the word
    exactly (accents ignored), so ordinary words are never mistaken for towns.
    """
    words = re.findall(r"[A-Za-z]{4,}", text)
    candidates = [w for w in words if w.lower() not in NOT_PLACES and w.lower() not in ignore]
    for word in list(dict.fromkeys(candidates))[:4]:  # unique, in order, at most 4 lookups per question
        for hit in search(word, limit=5):
            if fold(hit.name) == fold(word):
                return replace(hit, source="query")
    return None
