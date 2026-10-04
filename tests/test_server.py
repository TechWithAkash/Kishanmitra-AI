"""API tests with network and heavy models mocked."""

import base64
import json
import pytest
from fastapi.testclient import TestClient

from kisanmitra import pipeline, places, server, speech, weather
from kisanmitra.guards import RateLimiter
from tests.conftest import make_forecast

client = TestClient(server.app)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(pipeline, "translate", lambda text, target, source="en", romanize=False: f"[{target}] {text}")
    monkeypatch.setattr(places, "search", lambda q, limit=6, language="en": [places.Place(q, 20.0, 73.8, "Maharashtra", q, "search")])
    monkeypatch.setattr(weather, "forecast", lambda lat, lon, days=5: make_forecast())
    monkeypatch.setattr(speech, "speak", lambda text, lang: b"MP3DATA")
    # generous limits by default so tests do not trip over each other
    monkeypatch.setattr(server, "normal_limiter", RateLimiter(10_000))
    monkeypatch.setattr(server, "heavy_limiter", RateLimiter(10_000))


def test_health_and_locations():
    assert client.get("/api/health").json()["ok"] is True
    assert "Nashik" in client.get("/api/locations").json()


def test_chat_returns_structured_weather():
    r = client.post("/api/chat", json={"text": "इंदौर में अगले दो दिन बारिश होगी क्या?"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "weather" and body["lang"] == "hi"
    assert body["details"]["weather"]["days"][0]["rain_mm"] == 12.0
    assert body["details"]["weather"]["current"]["temp"] == 29.0
    assert "speech" not in body["details"]


def test_chat_uses_location_hint():
    body = client.post("/api/chat", json={"text": "will it rain tomorrow?", "location": "Pune"}).json()
    assert "Pune" in body["english"]


def test_chat_rejects_empty():
    assert client.post("/api/chat", json={"text": "   "}).status_code == 400


def test_voice_roundtrip(monkeypatch):
    monkeypatch.setattr(
        speech, "transcribe",
        lambda audio, lang=None: speech.Transcript("पुण्यात उद्या पाऊस पडेल का", "mr", 0.9, "google"),
    )
    r = client.post("/api/voice", files={"audio": ("a.webm", b"x" * 2000, "audio/webm")}, data={"lang_pref": "auto"})
    body = r.json()
    assert r.status_code == 200
    assert body["transcript"] == "पुण्यात उद्या पाऊस पडेल का" and body["lang"] == "mr"
    assert base64.b64decode(body["audio_b64"]) == b"MP3DATA"
    assert body["details"]["heard"]["engine"] == "google"


def test_voice_manual_language_is_passed_to_stt(monkeypatch):
    seen = {}

    def fake(audio, lang=None):
        seen["lang"] = lang
        return speech.Transcript("", lang or "hi", 1.0, "google")

    monkeypatch.setattr(speech, "transcribe", fake)
    body = client.post("/api/voice", files={"audio": ("a.webm", b"x" * 2000, "audio/webm")}, data={"lang_pref": "kn"}).json()
    assert seen["lang"] == "kn" and body["reply"] is None  # nothing heard → no reply


def test_voice_too_short():
    assert client.post("/api/voice", files={"audio": ("a.webm", b"x", "audio/webm")}).status_code == 400


def test_tts_endpoint_and_unsupported(monkeypatch):
    assert client.post("/api/tts", json={"text": "hi", "lang": "hi"}).content == b"MP3DATA"
    monkeypatch.setattr(speech, "speak", lambda text, lang: None)
    assert client.post("/api/tts", json={"text": "hi", "lang": "xx"}).status_code == 422


def test_transcribe_dictation(monkeypatch):
    monkeypatch.setattr(speech, "transcribe", lambda audio, lang=None: speech.Transcript("नमस्ते", "hi", 0.9, "google"))
    body = client.post("/api/transcribe", files={"audio": ("a.webm", b"x" * 2000, "audio/webm")}).json()
    assert body["text"] == "नमस्ते" and body["lang"] == "hi"


def test_tts_from_english_translates_first(monkeypatch):
    spoken = {}
    monkeypatch.setattr(server, "translate", lambda text, target: f"[{target}] {text}")
    monkeypatch.setattr(speech, "speak", lambda text, lang: spoken.setdefault("t", text).encode())
    client.post("/api/tts", json={"text": "Hello", "lang": "hi", "from_english": True})
    assert spoken["t"] == "[hi] Hello"


def test_chat_with_gps_place_and_follow_up_context():
    place = {"name": "Shalimar", "lat": 20.0, "lon": 73.78, "state": "Maharashtra", "district": "Nashik"}
    body = client.post("/api/chat", json={"text": "will it rain tomorrow?", "place": place}).json()
    assert "Weather for Shalimar, Nashik, Maharashtra" in body["english"] and body["details"]["place_from"] == "saved"
    body = client.post("/api/chat", json={"text": "aur pune me?", "context": {"intent": "weather"}}).json()
    assert body["intent"] == "weather" and body["details"]["follow_up"] is True


def test_chat_rejects_invalid_place_and_overlong_text():
    assert client.post("/api/chat", json={"text": "hi", "place": {"name": "X", "lat": 999}}).status_code == 422
    assert client.post("/api/chat", json={"text": "x" * 5000}).status_code == 422


def test_voice_accepts_place_and_context_as_json_forms(monkeypatch):
    monkeypatch.setattr(speech, "transcribe", lambda audio, lang=None: speech.Transcript("will it rain tomorrow", "en", 0.9, "google"))
    r = client.post(
        "/api/voice",
        files={"audio": ("a.webm", b"x" * 2000, "audio/webm")},
        data={"place": json.dumps({"name": "Satana", "lat": 20.5, "lon": 74.2}), "context": json.dumps({"intent": "weather"})},
    )
    assert r.status_code == 200 and "Weather for Satana" in r.json()["english"]
    bad = client.post("/api/voice", files={"audio": ("a.webm", b"x" * 2000, "audio/webm")}, data={"place": "{not json"})
    assert bad.status_code == 422


def test_places_search_and_reverse(monkeypatch):
    hits = client.get("/api/places/search", params={"q": "Satana"}).json()
    assert hits[0]["name"] == "Satana" and hits[0]["label"].startswith("Satana")
    assert client.get("/api/places/search", params={"q": "a"}).status_code == 422
    monkeypatch.setattr(places, "reverse", lambda lat, lon: places.Place("Shalimar", lat, lon, "Maharashtra", "Nashik", "gps"))
    body = client.get("/api/places/reverse", params={"lat": 20.0, "lon": 73.78}).json()
    assert body["label"] == "Shalimar, Nashik, Maharashtra" and body["source"] == "gps"
    assert client.get("/api/places/reverse", params={"lat": 200, "lon": 1}).status_code == 422


def test_rate_limit_returns_429_with_retry_after(monkeypatch):
    monkeypatch.setattr(server, "normal_limiter", RateLimiter(2))
    for _ in range(2):
        assert client.get("/api/locations").status_code == 200
    r = client.get("/api/locations")
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1
    assert client.get("/api/health").status_code == 200  # health checks are never limited


def test_heavy_endpoints_have_their_own_stricter_limit(monkeypatch):
    monkeypatch.setattr(server, "heavy_limiter", RateLimiter(1))
    files = {"audio": ("a.webm", b"x", "audio/webm")}
    assert client.post("/api/transcribe", files=files).status_code == 400   # allowed (but audio is too short)
    assert client.post("/api/transcribe", files=files).status_code == 429


def test_oversized_upload_is_rejected(monkeypatch):
    monkeypatch.setattr(server, "MAX_BYTES", 1000)
    r = client.post("/api/transcribe", files={"audio": ("a.webm", b"x" * 5000, "audio/webm")})
    assert r.status_code == 413


def test_unexpected_errors_return_json_not_a_stack_trace(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(server, "respond", boom)
    r = TestClient(server.app, raise_server_exceptions=False).post("/api/chat", json={"text": "hello"})
    assert r.status_code == 500 and "secret" not in r.text and r.json()["detail"]
    assert r.headers["X-Request-ID"]
