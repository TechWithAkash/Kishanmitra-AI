"""Free translation: Google first, MyMemory as backup, never show an error message as a translation."""

import pytest
import requests

from kisanmitra import translate as tr


class Resp:
    def __init__(self, data=None, status=200):
        self._data, self.status_code = data, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code), response=self)

    def json(self):
        return self._data


def gtx_ok(text):
    return Resp([[[f"HI:{text}", text, None, None], [None, None, f"roman:{text}"]]])


def mymemory_ok(text):
    return Resp({"responseStatus": 200, "responseData": {"translatedText": f"MM:{text}"}})


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    tr._cache.clear()
    tr._gtx_blocked_until = 0.0
    monkeypatch.setattr(tr, "ALLOW_MYMEMORY", True)   # most tests exercise the backup path; one checks it is off by default
    yield
    tr._gtx_blocked_until = 0.0


def install(monkeypatch, gtx, mymemory):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append("gtx" if "googleapis" in url else "mymemory")
        return (gtx if "googleapis" in url else mymemory)(params)

    monkeypatch.setattr(tr.requests, "get", fake_get)
    return calls


def test_google_translation_and_romanization(monkeypatch):
    install(monkeypatch, lambda p: gtx_ok(p["q"]), lambda p: mymemory_ok(p["q"]))
    assert tr.translate_ex("hello", "hi") == ("HI:hello", True)
    assert tr.translate_ex("hello", "hi", romanize=True) == ("roman:hello", True)


def test_rate_limited_google_falls_back_to_mymemory_and_is_skipped_for_a_while(monkeypatch):
    calls = install(monkeypatch, lambda p: Resp(status=429), lambda p: mymemory_ok(p["q"]))
    assert tr.translate_ex("hello", "hi") == ("MM:hello", True)
    assert tr.translate_ex("good morning", "hi") == ("MM:good morning", True)
    assert calls.count("gtx") == 1   # the second call did not even try Google (circuit breaker)


def test_long_text_is_split_for_mymemorys_500_character_limit(monkeypatch):
    seen = []
    install(monkeypatch, lambda p: Resp(status=429), lambda p: seen.append(len(p["q"])) or mymemory_ok(p["q"]))
    text = "\n".join(f"- {d} Oct: 22 to 33 degrees C, clear sky, rain 0.0 mm (0% chance)" for d in range(1, 12))
    assert len(text) > 500
    out, ok = tr.translate_ex(text, "hi")
    assert ok and len(seen) >= 2 and max(seen) <= 450
    assert out.count("MM:") == len(seen)


def test_an_error_message_is_never_returned_as_a_translation(monkeypatch):
    bad = lambda p: Resp({"responseStatus": 403, "responseData": {"translatedText": "QUERY LENGTH LIMIT EXCEEDED. MAX ALLOWED QUERY : 500 CHARS"}})
    install(monkeypatch, lambda p: Resp(status=429), bad)
    assert tr.translate_ex("hello", "hi") == ("hello", False)   # original text back, and the caller is told


def test_a_quota_warning_inside_an_ok_reply_is_rejected(monkeypatch):
    warn = lambda p: Resp({"responseStatus": 200, "responseData": {"translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY"}})
    install(monkeypatch, lambda p: Resp(status=429), warn)
    assert tr.translate_ex("hello", "hi")[1] is False


def test_failures_are_not_cached(monkeypatch):
    install(monkeypatch, lambda p: Resp(status=429), lambda p: Resp(status=500))
    assert tr.translate_ex("hello", "hi") == ("hello", False)
    install(monkeypatch, lambda p: gtx_ok(p["q"]), lambda p: mymemory_ok(p["q"]))
    tr._gtx_blocked_until = 0.0
    assert tr.translate_ex("hello", "hi") == ("HI:hello", True)   # recovered: the earlier failure did not stick


def test_successes_are_cached(monkeypatch):
    calls = install(monkeypatch, lambda p: gtx_ok(p["q"]), lambda p: mymemory_ok(p["q"]))
    tr.translate_ex("hello", "hi")
    tr.translate_ex("hello", "hi")
    assert calls == ["gtx"]


def test_same_language_and_empty_text_need_no_service(monkeypatch):
    calls = install(monkeypatch, lambda p: gtx_ok(p["q"]), lambda p: mymemory_ok(p["q"]))
    assert tr.translate_ex("hello", "en", source="en") == ("hello", True)
    assert tr.translate_ex("   ", "hi") == ("   ", True)
    assert calls == []


def test_split_text_respects_the_limit_and_loses_nothing():
    text = ("word " * 300).strip()
    parts = tr.split_text(text, 450)
    assert max(map(len, parts)) <= 450 and " ".join(parts).split() == text.split()


def test_unknown_source_language_uses_mymemorys_autodetect(monkeypatch):
    pairs = []
    install(monkeypatch, lambda p: Resp(status=429), lambda p: pairs.append(p["langpair"]) or mymemory_ok(p["q"]))
    assert tr.translate_ex("kal baarish hogi kya", "en", source="auto") == ("MM:kal baarish hogi kya", True)
    assert pairs == ["Autodetect|en"]   # not "en|en", which MyMemory rejects


def test_mymemory_is_not_used_unless_explicitly_enabled(monkeypatch):
    calls = install(monkeypatch, lambda p: Resp(status=429), lambda p: mymemory_ok(p["q"]))
    monkeypatch.setattr(tr, "ALLOW_MYMEMORY", False)
    assert tr.translate_ex("hello", "hi") == ("hello", False)
    assert "mymemory" not in calls


def test_successful_translations_survive_a_restart_even_if_google_is_blocked(monkeypatch):
    install(monkeypatch, lambda p: gtx_ok(p["q"]), lambda p: mymemory_ok(p["q"]))
    assert tr.translate_ex("Spray Mancozeb 2.5 g per litre.", "hi") == ("HI:Spray Mancozeb 2.5 g per litre.", True)
    # "restart": memory is empty, and Google now refuses everything
    tr._cache.clear()
    monkeypatch.setattr(tr, "_disk", None)
    calls = install(monkeypatch, lambda p: Resp(status=429), lambda p: Resp(status=500))
    monkeypatch.setattr(tr, "ALLOW_MYMEMORY", False)
    assert tr.translate_ex("Spray Mancozeb 2.5 g per litre.", "hi") == ("HI:Spray Mancozeb 2.5 g per litre.", True)
    assert calls == []


def test_a_corrupt_cache_line_does_not_break_translation(monkeypatch, tmp_path):
    (tmp_path / "translations.jsonl").write_text('{"k": "abc", "v": "x"}\n{this is not json\n')
    monkeypatch.setattr(tr, "_disk", None)
    install(monkeypatch, lambda p: gtx_ok(p["q"]), lambda p: mymemory_ok(p["q"]))
    assert tr.translate_ex("hello", "hi") == ("HI:hello", True)
