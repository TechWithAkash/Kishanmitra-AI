"""Shared test setup: never touch the real network or the real cache directory."""

import pytest

from kisanmitra import mandi, places, weather
from kisanmitra.config import settings


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    # A temporary cache directory, so tests never read or write the real mandi cache.
    monkeypatch.setattr(mandi, "settings", type("S", (), {"cache_dir": tmp_path})())
    # Any test that forgets to mock the network fails loudly instead of calling a real API.
    def no_network(*a, **k):
        raise AssertionError("test tried to use the real network")
    monkeypatch.setattr(places.requests, "get", no_network)
    monkeypatch.setattr(weather.requests, "get", no_network)
    monkeypatch.setattr(mandi.requests, "get", no_network)
    places._search.cache_clear()
    places._reverse.cache_clear()
    weather._cache.clear()
    yield


def make_forecast(rain_mm=12.0, rain_chance=80, humidity=70):
    from datetime import date

    return weather.Forecast(
        current=weather.Current(temp=29.0, humidity=humidity, wind_kmh=9.0, code=2, description="Partly cloudy"),
        days=[
            weather.DayForecast(date(2026, 10, 6), 21, 32, rain_mm, rain_chance, 8, 61, "Light rain"),
            weather.DayForecast(date(2026, 10, 7), 21, 31, 0.0, 10, 8, 1, "Mainly clear"),
            weather.DayForecast(date(2026, 10, 8), 20, 30, 0.0, 5, 8, 0, "Clear sky"),
        ],
    )


NASHIK = places.Place("Nashik", 19.99, 73.79, "Maharashtra", "Nashik", "search")
