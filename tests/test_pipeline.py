"""End-to-end pipeline tests with all network calls mocked."""

import pytest
import requests

from kisanmitra import mandi, pipeline, places, weather
from tests.conftest import NASHIK, make_forecast


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(pipeline, "translate", lambda text, target, source="en", romanize=False: f"[{target}{'-rm' if romanize else ''}] {text}")
    monkeypatch.setattr(places, "search", lambda q, limit=6, language="en": [places.Place(q, 20.0, 73.8, "Maharashtra", q, "search")])
    monkeypatch.setattr(weather, "forecast", lambda lat, lon, days=5: make_forecast())

    def api_down(*a, **k):  # tests that need live prices install their own mock
        raise requests.ConnectionError("down")
    monkeypatch.setattr(mandi, "_fetch_live", api_down)


def test_crop_disease_romanized_hindi():
    r = pipeline.respond("mera tamatar ka paudha peela ho raha hai, kya karu?")
    assert r.intent == "crop_disease"
    assert "Early blight" in r.english
    assert r.text.startswith("[hi-rm]")  # replied in romanized Hindi


def test_price_uses_sample_when_api_down_and_nothing_saved(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(mandi, "_fetch_live", boom)
    r = pipeline.respond("नाशिक मध्ये कांद्याचा भाव काय आहे?")
    assert r.intent == "market_price" and r.lang == "mr"
    assert r.details["mandi"]["source"] == "sample"
    assert "SAMPLE" in r.english and "Lasalgaon" in r.english


def test_price_falls_back_to_saved_prices_when_api_down(monkeypatch):
    rows = [{"state": "Maharashtra", "district": "Nashik", "market": "Lasalgaon", "commodity": "Onion",
             "arrival_date": "05/10/2026", "modal_price": "1900", "min_price": "1500", "max_price": "2200"}]
    monkeypatch.setattr(mandi, "_fetch_live", lambda commodity, state: rows)
    assert pipeline.respond("onion price in Nashik").details["mandi"]["source"] == "live"

    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(mandi, "_fetch_live", boom)
    r = pipeline.respond("onion price in Nashik")
    assert r.details["mandi"]["source"] == "cached"
    assert "saved" in r.english and "SAMPLE" not in r.english and "Lasalgaon" in r.english


def test_price_live_filters_to_district(monkeypatch):
    rows = [
        {"state": "Maharashtra", "district": "Pune", "market": "Pune", "commodity": "Onion",
         "arrival_date": "05/10/2026", "modal_price": "1900", "min_price": "1500", "max_price": "2200"},
        {"state": "Maharashtra", "district": "Nashik", "market": "Lasalgaon", "commodity": "Onion",
         "arrival_date": "05/10/2026", "modal_price": "1800", "min_price": "1400", "max_price": "2100"},
    ]
    monkeypatch.setattr(mandi, "_fetch_live", lambda commodity, state: rows)
    r = pipeline.respond("What is the onion price in Nashik?")
    assert r.details["mandi"]["scope"] == "district"
    assert "Lasalgaon" in r.english and "Pune (Pune)" not in r.english


def test_price_uses_saved_gps_district_and_state(monkeypatch):
    seen = {}
    monkeypatch.setattr(mandi, "get_prices", lambda commodity, district=None, state=None:
                        seen.update(district=district, state=state) or mandi.PriceResult())
    pipeline.respond("onion price today", place=places.Place("Shalimar", 20.0, 73.78, "Delhi", "Nashik", "gps"))
    assert seen == {"district": "Nashik", "state": "NCT of Delhi"}  # state renamed the way Agmarknet spells it


def test_weather_for_saved_place_gives_current_conditions_and_tip():
    r = pipeline.respond("will it rain tomorrow?", place=NASHIK)
    assert r.intent == "weather" and r.details["place_from"] == "saved"
    assert "Weather for Nashik, Maharashtra" in r.english and "Now: 29 degrees C" in r.english
    assert "postpone spraying" in r.english
    assert r.details["weather"]["current"]["humidity"] == 70 and len(r.details["weather"]["days"]) == 3


def test_weather_for_any_town_named_in_the_question():
    r = pipeline.respond("will it rain in Satana tomorrow")
    assert r.details["place_from"] == "question"
    assert r.details["place"]["name"] == "Satana"
    assert "Weather for Satana" in r.english


def test_place_in_the_question_beats_the_saved_place():
    r = pipeline.respond("इंदौर में अगले दो दिन बारिश होगी क्या?", place=NASHIK)
    assert r.details["place"]["name"] == "Indore" and r.details["place_from"] == "question"


def test_weather_without_any_place_asks_and_flags_it():
    r = pipeline.respond("will it rain tomorrow?")
    assert "Which village or town" in r.english and r.details["needs_location"] is True


def test_weather_service_down_is_reported_politely(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(weather, "forecast", boom)
    assert "not reachable" in pipeline.respond("will it rain tomorrow?", place=NASHIK).english


def test_unknown_place_is_not_invented(monkeypatch):
    monkeypatch.setattr(places, "search", lambda *a, **k: [])
    r = pipeline.respond("weather for Xyzabc", place=None)
    assert r.details.get("needs_location") is True


def test_legacy_city_name_is_still_accepted():
    r = pipeline.respond("will it rain tomorrow?", default_location="Pune")
    assert "Pune" in r.english and r.details["place_from"] == "saved"


def test_follow_up_keeps_the_previous_topic():
    # "and in Pune?" right after a price question
    r = pipeline.respond("aur pune me?", context={"intent": "market_price", "crop": "onion"})
    assert r.intent == "market_price" and r.entities["crop"] == "onion" and r.details["follow_up"] is True


def test_follow_up_survives_a_confident_but_wrong_reclassification(monkeypatch):
    # The translate-and-retry step may read "And in Pune?" as some other topic with high confidence.
    monkeypatch.setattr(pipeline, "translate", lambda text, target, source="en", romanize=False: "And in Pune?" if target == "en" else text)
    monkeypatch.setattr(pipeline, "predict_intent", lambda t: ("general", 0.30) if t == "aur pune me?" else ("crop_disease", 0.9))
    r = pipeline.respond("aur pune me?", context={"intent": "market_price", "crop": "onion"})
    assert r.intent == "market_price" and r.details["follow_up"] is True


def test_follow_up_is_not_applied_to_a_clear_new_question():
    r = pipeline.respond("will it rain in Pune tomorrow?", context={"intent": "market_price", "crop": "onion"})
    assert r.intent == "weather" and "follow_up" not in r.details


def test_missing_slots_ask_follow_up():
    assert "Which crop" in pipeline.respond("mandi me aaj kya bhav hai").english


def test_english_reply_not_translated():
    r = pipeline.respond("What can you do?")
    assert r.text == r.english
