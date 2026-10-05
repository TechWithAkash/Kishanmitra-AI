"""OpenWeather as the primary weather source, Open-Meteo as the fallback (network mocked)."""

from datetime import datetime, timedelta, timezone

import pytest
import requests

from kisanmitra import pipeline, places, weather
from kisanmitra.config import load_env, redact

KEY = "abcdef0123456789abcdef0123456789"
IST = 19800  # +05:30 in seconds


class Resp:
    def __init__(self, data=None, status=200):
        self._data, self.status_code = data, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error for url: https://x/y?appid={KEY}", response=self)

    def json(self):
        return self._data


def owm_current(temp=29.5, humidity=70, wind_ms=2.0, wid=801, name="Satānā"):
    return {"name": name, "main": {"temp": temp, "humidity": humidity, "feels_like": temp + 3},
            "wind": {"speed": wind_ms}, "weather": [{"id": wid, "description": "few clouds"}]}


def slot(local_dt, temp, wid=800, desc="clear sky", pop=0.0, rain=None, wind_ms=3.0):
    """One 3-hour forecast entry. `local_dt` is local (IST) time; OpenWeather stores UTC."""
    utc = local_dt - timedelta(seconds=IST)
    e = {"dt": int(utc.replace(tzinfo=timezone.utc).timestamp()), "main": {"temp": temp, "temp_min": temp - 1, "temp_max": temp + 1},
         "weather": [{"id": wid, "description": desc}], "pop": pop, "wind": {"speed": wind_ms}}
    if rain:
        e["rain"] = {"3h": rain}
    return e


def owm_forecast(slots):
    return {"cnt": len(slots), "city": {"name": "Satānā", "timezone": IST}, "list": slots}


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", KEY)


def route(monkeypatch, current, forecast, open_meteo=None):
    """Make requests.get answer for OpenWeather (and optionally Open-Meteo); return the calls made."""
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        if "openweathermap.org/data/2.5/weather" in url:
            return current if isinstance(current, Resp) else Resp(current)
        if "openweathermap.org/data/2.5/forecast" in url:
            return forecast if isinstance(forecast, Resp) else Resp(forecast)
        if "open-meteo.com" in url:
            if open_meteo is None:
                raise AssertionError("Open-Meteo should not have been called")
            return open_meteo if isinstance(open_meteo, Resp) else Resp(open_meteo)
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(weather.requests, "get", fake_get)
    return calls


def tomorrow_slots():
    today = (datetime.now(timezone.utc) + timedelta(seconds=IST)).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    d1 = today + timedelta(days=1)
    return today, [
        slot(today + timedelta(hours=21), 24.0),
        slot(d1 + timedelta(hours=0), 23.0),
        slot(d1 + timedelta(hours=9), 27.0, 500, "light rain", pop=0.7, rain=2.5, wind_ms=5.0),
        slot(d1 + timedelta(hours=12), 30.0, 501, "moderate rain", pop=0.9, rain=4.0, wind_ms=7.0),
        slot(d1 + timedelta(hours=21), 25.0, 802, "scattered clouds", pop=0.1),
    ]


def test_openweather_is_used_when_a_key_is_set(with_key, monkeypatch):
    _, slots = tomorrow_slots()
    calls = route(monkeypatch, owm_current(), owm_forecast(slots))
    fc = weather.forecast(20.59, 74.2)
    assert fc.source == "openweather" and fc.station == "Satānā"
    assert any("data/2.5/weather" in c for c in calls) and any("data/2.5/forecast" in c for c in calls)


def test_current_conditions_are_converted(with_key, monkeypatch):
    _, slots = tomorrow_slots()
    route(monkeypatch, owm_current(temp=29.5, humidity=70, wind_ms=2.0, wid=801), owm_forecast(slots))
    c = weather.forecast(20.59, 74.2).current
    assert (c.temp, c.humidity, c.wind_kmh) == (29.5, 70, 7.2)   # 2.0 m/s = 7.2 km/h
    assert c.code == 1 and c.description == "Few clouds" and c.feels_like == 32.5


def test_three_hour_slots_become_local_days(with_key, monkeypatch):
    today, slots = tomorrow_slots()
    route(monkeypatch, owm_current(temp=26.0), owm_forecast(slots))
    days = weather.forecast(20.59, 74.2).days
    assert [d.day for d in days] == [today.date(), (today + timedelta(days=1)).date()]
    tomorrow = days[1]
    assert (tomorrow.t_min, tomorrow.t_max) == (22.0, 31.0)          # lowest temp_min, highest temp_max
    assert tomorrow.rain_mm == 6.5 and tomorrow.rain_chance == 90    # 2.5 + 4.0 mm; the highest chance of rain
    assert tomorrow.wind_kmh == 25.2                                  # 7 m/s
    assert tomorrow.description == "Moderate rain" and tomorrow.code == 63   # the wettest slot represents the day


def test_a_late_evening_slot_belongs_to_the_local_not_the_utc_day(with_key, monkeypatch):
    today, _ = tomorrow_slots()
    d1 = today + timedelta(days=1)
    # 23:30 India time is 18:00 UTC of the SAME day; 01:00 India time is still the previous UTC day
    slots = [slot(today + timedelta(hours=21), 24.0), slot(d1 + timedelta(hours=1), 22.0), slot(d1 + timedelta(hours=23, minutes=30), 21.0)]
    route(monkeypatch, owm_current(), owm_forecast(slots))
    days = weather.forecast(20.59, 74.2).days
    assert [d.day for d in days] == [today.date(), d1.date()]
    assert days[1].t_min == 20.0


def test_today_includes_the_current_temperature(with_key, monkeypatch):
    today, slots = tomorrow_slots()
    route(monkeypatch, owm_current(temp=35.0), owm_forecast(slots))   # hotter right now than any remaining slot
    assert weather.forecast(20.59, 74.2).days[0].t_max == 35.0


@pytest.mark.parametrize("owm_id, wmo", [(800, 0), (802, 2), (804, 3), (211, 95), (212, 99), (500, 61), (503, 65), (521, 80),
                                         (601, 73), (741, 45), (781, 99)])
def test_condition_codes_map_to_the_icon_set(owm_id, wmo):
    assert weather.owm_to_wmo(owm_id) == wmo


def test_falls_back_to_open_meteo_when_openweather_rejects_the_key(with_key, monkeypatch, caplog):
    open_meteo = {"daily": {"time": ["2026-10-06"], "weather_code": [1], "temperature_2m_max": [33.0], "temperature_2m_min": [22.0],
                            "precipitation_sum": [0.0], "precipitation_probability_max": [3], "wind_speed_10m_max": [9.0]},
                  "current": {"temperature_2m": 28.0, "relative_humidity_2m": 60, "wind_speed_10m": 5.0, "weather_code": 1}}
    route(monkeypatch, Resp(status=401), Resp(status=401), open_meteo=open_meteo)
    with caplog.at_level("WARNING"):
        fc = weather.forecast(20.59, 74.2)
    assert fc.source == "open-meteo" and fc.current.temp == 28.0
    assert KEY not in caplog.text  # the warning that was logged does not contain the key


def test_without_a_key_only_open_meteo_is_used(monkeypatch):
    open_meteo = {"daily": {"time": ["2026-10-06"], "weather_code": [0], "temperature_2m_max": [33.0], "temperature_2m_min": [22.0],
                            "precipitation_sum": [0.0], "precipitation_probability_max": [3], "wind_speed_10m_max": [9.0]}}
    calls = route(monkeypatch, None, None, open_meteo=open_meteo)
    assert weather.forecast(20.59, 74.2).source == "open-meteo"
    assert all("openweathermap" not in c for c in calls)


def test_when_every_provider_fails_the_error_is_safe(with_key, monkeypatch):
    route(monkeypatch, Resp(status=500), Resp(status=500), open_meteo=Resp(status=503))
    with pytest.raises(weather.WeatherError) as err:
        weather.forecast(20.59, 74.2)
    assert KEY not in str(err.value)


def test_forecasts_are_cached(with_key, monkeypatch):
    _, slots = tomorrow_slots()
    calls = route(monkeypatch, owm_current(), owm_forecast(slots))
    weather.forecast(20.59, 74.2)
    weather.forecast(20.591, 74.201)   # ~100 m away: same cache cell
    assert len(calls) == 2             # one current + one forecast request in total


def test_the_pipeline_never_sends_the_key_to_the_client(with_key, monkeypatch):
    monkeypatch.setattr(pipeline, "translate", lambda text, target, **k: text)
    route(monkeypatch, Resp(status=401), Resp(status=401), open_meteo=Resp(status=503))
    r = pipeline.respond("will it rain tomorrow?", place=places.Place("Satana", 20.6, 74.2, "Maharashtra", "Nashik"))
    assert "not reachable" in r.english and KEY not in str(r)


def test_redact_removes_keys_from_any_text(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", KEY)
    assert KEY not in redact(f"401 Client Error for url: https://api.openweathermap.org/x?lat=1&appid={KEY}&units=metric")
    assert redact("https://x/y?api-key=SECRETVALUE123&format=json") == "https://x/y?api-key=***&format=json"
    assert redact(f"the key {KEY} itself") == "the key *** itself"
    assert redact("nothing secret here") == "nothing secret here"


def test_env_file_is_loaded_without_overriding_real_environment(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("KM_TEST_A=from_file\nKM_TEST_B=from_file\n")
    monkeypatch.setenv("KM_TEST_B", "from_shell")
    monkeypatch.delenv("KM_TEST_A", raising=False)
    load_env(env)
    import os
    assert os.environ["KM_TEST_A"] == "from_file" and os.environ["KM_TEST_B"] == "from_shell"
    monkeypatch.delenv("KM_TEST_A")


def test_places_search_falls_back_to_openweather_geocoding(with_key, monkeypatch):
    def fake_get(url, params=None, timeout=None):
        if "open-meteo" in url:
            raise requests.ConnectionError("down")
        assert "geo/1.0/direct" in url and params["q"] == "Satana,IN"
        return Resp([{"name": "Satana", "lat": 20.6, "lon": 74.2, "state": "Maharashtra", "country": "IN"}])
    monkeypatch.setattr(places.requests, "get", fake_get)
    assert [p.label() for p in places.search("Satana")] == ["Satana, Maharashtra"]


def test_reverse_geocoding_falls_back_to_openweather_when_openstreetmap_is_down(with_key, monkeypatch):
    monkeypatch.setattr(places.time, "sleep", lambda s: None)

    def fake_get(url, params=None, headers=None, timeout=None):
        if "nominatim" in url:
            raise requests.ConnectionError("down")
        assert "geo/1.0/reverse" in url
        return Resp([{"name": "Baglan Taluka", "state": "Maharashtra"}])
    monkeypatch.setattr(places.requests, "get", fake_get)
    p = places.reverse(20.5948, 74.2030)
    assert (p.name, p.state, p.lat) == ("Baglan Taluka", "Maharashtra", 20.5948)


def test_a_trivial_chance_of_rain_does_not_make_a_rainy_day(with_key, monkeypatch):
    today, _ = tomorrow_slots()
    d1 = today + timedelta(days=1)
    slots = [slot(today + timedelta(hours=21), 24.0),
             slot(d1 + timedelta(hours=9), 28.0, 500, "light rain", pop=0.2, rain=0.1),   # 20%, 0.1 mm
             slot(d1 + timedelta(hours=12), 31.0), slot(d1 + timedelta(hours=15), 32.0)]
    route(monkeypatch, owm_current(), owm_forecast(slots))
    day = weather.forecast(20.59, 74.2).days[1]
    assert day.code == 0 and day.description == "Clear sky"
    assert day.rain_chance == 20 and day.rain_mm == 0.1   # the numbers are still reported honestly
