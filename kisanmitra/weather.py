"""Weather + farming tips for any latitude/longitude.

Primary source: OpenWeather (free plan: current weather + 5-day/3-hour forecast).
Set OPENWEATHER_API_KEY in .env. If the key is missing, or OpenWeather is unreachable or
rejects the request, the free Open-Meteo service (no key) is used automatically, so the
farmer still gets a forecast.

API keys appear in the URLs of failed requests, so every error raised from this module is
passed through `redact()` first: a key must never reach a log file or a browser.
"""

import logging
import os
import threading
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import requests

from kisanmitra.config import redact

log = logging.getLogger("kisanmitra.weather")

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 600   # forecasts change slowly; also keeps us far below OpenWeather's 60 calls/minute
TIMEOUT = 10

# WMO weather codes (used by Open-Meteo, and as the common code the UI draws icons from) → description.
WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Rain showers", 81: "Rain showers",
    82: "Violent rain showers", 85: "Snow showers", 86: "Snow showers", 95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


class WeatherError(RuntimeError):
    """The weather could not be fetched. The message is safe to log or show (secrets removed)."""


def describe(code: int | None) -> str:
    return WMO.get(code if code is not None else -1, "Unknown")


def openweather_key() -> str:
    return os.environ.get("OPENWEATHER_API_KEY", "").strip()


@dataclass
class Current:
    temp: float
    humidity: int
    wind_kmh: float
    code: int
    description: str
    feels_like: float | None = None


@dataclass
class DayForecast:
    day: date
    t_min: float
    t_max: float
    rain_mm: float
    rain_chance: int
    wind_kmh: float
    code: int = 0
    description: str = ""


@dataclass
class Forecast:
    current: Current | None
    days: list[DayForecast]
    source: str = "open-meteo"        # "openweather" | "open-meteo"
    station: str | None = None        # nearest place OpenWeather measured at, e.g. "Satānā"


_cache: dict[tuple, tuple[float, Forecast]] = {}
_cache_lock = threading.Lock()


def _get_json(url: str, params: dict) -> dict:
    """GET with one retry (free APIs occasionally drop a request). Errors never contain the API key."""
    last = "request failed"
    for _ in range(2):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            last = f"HTTP {status} from {url.split('?')[0]}"
            if 400 <= status < 500 and status != 429:
                break  # 401 / 404 etc.: retrying cannot help
        except (requests.RequestException, ValueError) as exc:
            last = f"{type(exc).__name__}: {exc}"
    raise WeatherError(redact(last))


# ---------------------------------------------------------------- OpenWeather

def owm_to_wmo(owm_id: int) -> int:
    """OpenWeather condition id → WMO code (so one set of icons/descriptions covers both providers)."""
    if owm_id == 800:
        return 0
    if owm_id == 801:
        return 1
    if owm_id == 802:
        return 2
    if owm_id in (803, 804):
        return 3
    if 200 <= owm_id < 300:
        return 99 if owm_id in (202, 212, 221, 232) else 95
    if 300 <= owm_id < 400:
        return 51 if owm_id in (300, 310) else 53 if owm_id in (301, 311, 313, 321) else 55
    if owm_id == 500:
        return 61
    if owm_id == 501:
        return 63
    if owm_id in (502, 503, 504):
        return 65
    if owm_id == 511:
        return 66
    if owm_id in (520, 521):
        return 80
    if owm_id in (522, 531):
        return 82
    if 600 <= owm_id < 700:
        return 71 if owm_id == 600 else 73 if owm_id in (601, 615, 616) else 75 if owm_id in (602, 622) else 77
    if owm_id == 781:
        return 99
    if 700 <= owm_id < 800:
        return 45  # mist, haze, smoke, dust, fog
    return 3


def _pick_condition(entries: list[dict]) -> tuple[int, str]:
    """The weather to show for a whole day: the wettest 3-hour slot if it rains, else the most common."""
    # A slot only counts as wet if rain is actually likely (not a 20% chance of 0.1 mm).
    wet = [
        e for e in entries
        if 200 <= e["weather"][0]["id"] < 700 and (e.get("pop", 0) >= 0.4 or e.get("rain", {}).get("3h", 0.0) >= 1.0)
    ]
    if wet:
        w = max(wet, key=lambda e: (e.get("pop", 0), e["weather"][0]["id"]))["weather"][0]
    else:
        common = Counter(e["weather"][0]["id"] for e in entries).most_common(1)[0][0]
        w = next(e["weather"][0] for e in entries if e["weather"][0]["id"] == common)
    return owm_to_wmo(w["id"]), w["description"].capitalize()


def _openweather(lat: float, lon: float, days: int) -> Forecast:
    base = {"lat": lat, "lon": lon, "units": "metric", "appid": openweather_key()}
    cur = _get_json(f"{OPENWEATHER_URL}/weather", base)
    fc = _get_json(f"{OPENWEATHER_URL}/forecast", base)

    cw = cur["weather"][0]
    current = Current(
        temp=cur["main"]["temp"],
        humidity=round(cur["main"]["humidity"]),
        wind_kmh=round(cur["wind"].get("speed", 0.0) * 3.6, 1),   # OpenWeather gives m/s
        code=owm_to_wmo(cw["id"]),
        description=cw["description"].capitalize(),
        feels_like=cur["main"].get("feels_like"),
    )

    # The forecast is in 3-hour steps with UTC timestamps: group them by the farmer's LOCAL calendar day.
    offset = timedelta(seconds=fc["city"].get("timezone", 0))
    by_day: dict[date, list[dict]] = {}
    for entry in fc["list"]:
        local = datetime.fromtimestamp(entry["dt"], tz=timezone.utc) + offset
        by_day.setdefault(local.date(), []).append(entry)

    today = (datetime.now(timezone.utc) + offset).date()
    out: list[DayForecast] = []
    for day in sorted(by_day):
        if day < today:
            continue
        entries = by_day[day]
        t_min = min(e["main"]["temp_min"] for e in entries)
        t_max = max(e["main"]["temp_max"] for e in entries)
        if day == today:  # the slots already gone are missing from today's list: include "now"
            t_min, t_max = min(t_min, current.temp), max(t_max, current.temp)
        code, description = _pick_condition(entries)
        out.append(DayForecast(
            day=day,
            t_min=round(t_min, 1),
            t_max=round(t_max, 1),
            rain_mm=round(sum(e.get("rain", {}).get("3h", 0.0) for e in entries), 1),
            rain_chance=round(max(e.get("pop", 0.0) for e in entries) * 100),
            wind_kmh=round(max(e["wind"].get("speed", 0.0) for e in entries) * 3.6, 1),
            code=code,
            description=description,
        ))
    if not out:
        raise WeatherError("OpenWeather returned no forecast")
    return Forecast(current=current, days=out[:days], source="openweather", station=cur.get("name") or None)


# ---------------------------------------------------------------- Open-Meteo (free, no key)

def _open_meteo(lat: float, lon: float, days: int) -> Forecast:
    data = _get_json(OPEN_METEO_URL, {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "precipitation_probability_max,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": days,
    })
    d = data["daily"]
    cur = data.get("current")
    return Forecast(
        current=Current(
            temp=cur["temperature_2m"],
            humidity=round(cur["relative_humidity_2m"]),
            wind_kmh=cur["wind_speed_10m"],
            code=cur["weather_code"],
            description=describe(cur["weather_code"]),
            feels_like=cur.get("apparent_temperature"),
        ) if cur else None,
        days=[
            DayForecast(
                day=date.fromisoformat(d["time"][i]),
                t_min=d["temperature_2m_min"][i],
                t_max=d["temperature_2m_max"][i],
                rain_mm=d["precipitation_sum"][i] or 0.0,
                rain_chance=d["precipitation_probability_max"][i] or 0,
                wind_kmh=d["wind_speed_10m_max"][i] or 0.0,
                code=d["weather_code"][i] or 0,
                description=describe(d["weather_code"][i]),
            )
            for i in range(len(d["time"]))
        ],
        source="open-meteo",
    )


# ---------------------------------------------------------------- public API

def forecast(lat: float, lon: float, days: int = 5) -> Forecast:
    """Current conditions + daily forecast for exact coordinates. Cached for 10 minutes."""
    key = (round(lat, 2), round(lon, 2), days, bool(openweather_key()))
    with _cache_lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]

    result: Forecast | None = None
    if openweather_key():
        try:
            result = _openweather(lat, lon, days)
        except (WeatherError, KeyError, IndexError, TypeError, ValueError) as exc:
            log.warning("OpenWeather failed, using Open-Meteo instead: %s", redact(f"{type(exc).__name__}: {exc}"))
    if result is None:
        try:
            result = _open_meteo(lat, lon, days)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise WeatherError(f"Unexpected weather response ({type(exc).__name__})") from None

    with _cache_lock:
        if len(_cache) > 500:
            _cache.clear()
        _cache[key] = (time.monotonic(), result)
    return result


def farming_tips(days: list[DayForecast], current: Current | None = None) -> list[str]:
    tips = []
    if any(d.rain_mm >= 5 or d.rain_chance >= 60 for d in days[:2]):
        tips.append("Rain is likely in the next 2 days: postpone spraying and fertilizer application, and make sure fields drain well.")
    elif all(d.rain_mm < 1 for d in days[:3]):
        tips.append("No rain expected: plan irrigation, preferably in the early morning or evening.")
    if any(d.t_max >= 40 for d in days[:3]):
        tips.append("Very hot days ahead: irrigate in the evening and protect young plants from heat stress.")
    if any(d.t_min <= 5 for d in days[:3]):
        tips.append("Very cold nights ahead: light irrigation in the evening can protect crops from frost.")
    if any(d.wind_kmh >= 20 for d in days[:3]):
        tips.append("Strong winds expected: avoid spraying on those days because the spray will drift.")
    if current and current.humidity >= 85 and 18 <= current.temp <= 32:
        tips.append("Humid and warm: fungal diseases such as blight spread fast. Check your leaves for spots.")
    if not tips:
        tips.append("Weather looks normal: a good time for spraying and field work.")
    return tips
