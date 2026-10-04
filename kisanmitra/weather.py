"""Weather + farming tips from Open-Meteo (free, no API key). Works for any latitude/longitude."""

import threading
import time
from dataclasses import dataclass
from datetime import date

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 600

# WMO weather codes → short description.
WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Rain showers", 81: "Rain showers",
    82: "Violent rain showers", 85: "Snow showers", 86: "Snow showers", 95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


def describe(code: int | None) -> str:
    return WMO.get(code if code is not None else -1, "Unknown")


@dataclass
class Current:
    temp: float
    humidity: int
    wind_kmh: float
    code: int
    description: str


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


_cache: dict[tuple, tuple[float, Forecast]] = {}
_cache_lock = threading.Lock()


def _get_json(url: str, params: dict) -> dict:
    """GET with one retry: the free API occasionally drops a request."""
    for attempt in (1, 2):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


def forecast(lat: float, lon: float, days: int = 5) -> Forecast:
    key = (round(lat, 2), round(lon, 2), days)
    with _cache_lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]

    data = _get_json(FORECAST_URL, {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "precipitation_probability_max,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": days,
    })
    d = data["daily"]
    cur = data.get("current")
    result = Forecast(
        current=Current(
            temp=cur["temperature_2m"],
            humidity=round(cur["relative_humidity_2m"]),
            wind_kmh=cur["wind_speed_10m"],
            code=cur["weather_code"],
            description=describe(cur["weather_code"]),
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
    )
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
