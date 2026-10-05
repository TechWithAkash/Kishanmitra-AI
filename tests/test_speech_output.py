"""Text → speech: natural voice first, basic voice second, silence never silent (network mocked)."""

import pytest

from kisanmitra import speech


@pytest.fixture(autouse=True)
def isolated_voice(tmp_path, monkeypatch):
    monkeypatch.setattr(speech, "settings", type("S", (), {"cache_dir": tmp_path, "tts_rate": "-8%"})())
    monkeypatch.setattr(speech, "_edge_blocked_until", 0.0)


def test_the_natural_voice_is_preferred(monkeypatch):
    monkeypatch.setattr(speech, "_edge", lambda text, lang: b"NEURAL")
    monkeypatch.setattr(speech, "_gtts", lambda text, lang: pytest.fail("basic voice must not be used"))
    assert speech.speak("नमस्ते", "hi") == b"NEURAL"


def test_falls_back_to_the_basic_voice(monkeypatch):
    monkeypatch.setattr(speech, "_edge", lambda text, lang: None)
    monkeypatch.setattr(speech, "_gtts", lambda text, lang: b"BASIC")
    assert speech.speak("नमस्ते", "hi") == b"BASIC"


def test_returns_none_when_both_voices_fail_so_the_browser_can_speak_instead(monkeypatch):
    monkeypatch.setattr(speech, "_edge", lambda text, lang: None)
    monkeypatch.setattr(speech, "_gtts", lambda text, lang: None)
    assert speech.speak("नमस्ते", "hi") is None


def test_natural_voice_results_are_cached_and_survive_the_service_going_down(monkeypatch):
    calls = []
    monkeypatch.setattr(speech, "_edge", lambda text, lang: calls.append(1) or b"NEURAL")
    assert speech.speak("आज बारिश होगी", "hi") == b"NEURAL"
    monkeypatch.setattr(speech, "_edge", lambda text, lang: None)          # service is down now
    monkeypatch.setattr(speech, "_gtts", lambda text, lang: None)
    assert speech.speak("आज बारिश होगी", "hi") == b"NEURAL" and calls == [1]


def test_the_basic_voice_is_never_cached_so_the_natural_one_is_retried_later(monkeypatch):
    monkeypatch.setattr(speech, "_edge", lambda text, lang: None)
    monkeypatch.setattr(speech, "_gtts", lambda text, lang: b"BASIC")
    speech.speak("आज बारिश होगी", "hi")
    monkeypatch.setattr(speech, "_edge", lambda text, lang: b"NEURAL")
    assert speech.speak("आज बारिश होगी", "hi") == b"NEURAL"


def test_unsupported_language_and_empty_text_make_no_sound_and_no_request(monkeypatch):
    monkeypatch.setattr(speech, "_edge", lambda *a: pytest.fail("no request expected"))
    monkeypatch.setattr(speech, "_gtts", lambda *a: pytest.fail("no request expected"))
    assert speech.speak("hello", "xx") is None
    assert speech.speak("🌾  ", "hi") is None


def test_emoji_and_list_bullets_are_not_read_aloud():
    assert speech.clean_for_speech("🌾 नमस्ते!\n- तापमान 23°C 🌧️", "hi") == "नमस्ते!\nतापमान 23°C"
    assert speech.clean_for_speech("It is 23°C, 20% rain", "en") == "It is 23 degrees, 20 percent rain"


def test_the_natural_voice_is_skipped_for_a_minute_after_it_fails(monkeypatch):
    async def boom(text, voice):
        raise ConnectionError("offline")
    monkeypatch.setattr(speech, "_edge_stream", boom)
    monkeypatch.setattr(speech, "_gtts", lambda text, lang: b"BASIC")
    assert speech.speak("एक", "hi") == b"BASIC"
    monkeypatch.setattr(speech, "_edge_stream", lambda *a: pytest.fail("should be skipped while the breaker is open"))
    assert speech.speak("दो", "hi") == b"BASIC"


def test_every_indian_language_with_a_neural_voice_is_mapped():
    for lang in ("hi", "mr", "ta", "te", "bn", "gu", "kn", "ml", "ur", "en"):
        assert speech.EDGE_VOICES[lang].startswith(lang) and speech.EDGE_VOICES[lang].endswith("Neural")
