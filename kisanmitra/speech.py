"""Voice in / voice out — all free.

Speech → text is a two-step hybrid:
  1. Whisper (faster-whisper, runs locally) DETECTS which language is spoken, so the
     farmer never has to pick a language. Whisper is reliable at this.
  2. Google's free speech recognition WRITES OUT the words in that language. It is far
     more accurate than small Whisper for Indian languages like Telugu and Bengali.
     If Google is unreachable, Whisper's own transcript is used instead.
The Whisper model downloads once (~500 MB for "small"); change with WHISPER_MODEL.

Text → speech: Microsoft neural voices via edge-tts (natural, free), with gTTS as the backup.
"""

import asyncio
import hashlib
import io
import logging
import os
import re
import time
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from kisanmitra.config import settings

log = logging.getLogger("kisanmitra.speech")

TTS_LANGS = {"hi", "mr", "ta", "te", "bn", "gu", "kn", "ml", "pa", "ur", "en"}

# Whisper code → Google speech locale. Only these are considered when detecting the
# language; otherwise Marathi/Hindi speech is often mistaken for Nepali, Sanskrit, etc.
GOOGLE_LOCALES = {
    "hi": "hi-IN", "mr": "mr-IN", "ta": "ta-IN", "te": "te-IN", "bn": "bn-IN", "gu": "gu-IN",
    "kn": "kn-IN", "ml": "ml-IN", "pa": "pa-Guru-IN", "ur": "ur-IN", "en": "en-IN",
}

# Farming vocabulary given to Whisper as a spelling hint (fallback path only).
WHISPER_PROMPTS = {
    "hi": "किसान का सवाल: फसल, टमाटर, प्याज, आलू, गेहूं, धान, कपास, सोयाबीन, मिर्च, मंडी भाव, बारिश, मौसम, कीड़े, पत्ते पीले।",
    "mr": "शेतकऱ्याचा प्रश्न: पीक, टोमॅटो, कांदा, बटाटा, गहू, कापूस, सोयाबीन, मिरची, बाजार भाव, पाऊस, हवामान, कीड, पाने पिवळी.",
}


@dataclass
class Transcript:
    text: str
    lang: str            # language Whisper heard, e.g. "ta"
    lang_prob: float
    engine: str          # "google" or "whisper"


@lru_cache(maxsize=1)
def _whisper():
    from faster_whisper import WhisperModel  # imported lazily: text-only use never loads it

    return WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")


def detect_spoken_language(samples: np.ndarray) -> tuple[str, float]:
    _, _, all_probs = _whisper().detect_language(audio=samples)
    lang, prob = max(((l, p) for l, p in all_probs if l in GOOGLE_LOCALES), key=lambda x: x[1])
    # Spoken Hindi and Urdu sound alike; our farmers are far more likely Hindi speakers.
    return ("hi" if lang == "ur" else lang), prob


def _google_stt(samples: np.ndarray, lang: str) -> str:
    import speech_recognition as sr

    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes()
    return sr.Recognizer().recognize_google(sr.AudioData(pcm, 16000, 2), language=GOOGLE_LOCALES[lang])


def _whisper_stt(samples: np.ndarray, lang: str) -> str:
    segments, _ = _whisper().transcribe(
        samples, language=lang, initial_prompt=WHISPER_PROMPTS.get(lang), beam_size=5, vad_filter=True
    )
    return " ".join(s.text.strip() for s in segments).strip()


def transcribe(audio: bytes, lang: str | None = None) -> Transcript:
    """`lang` = language the user picked manually; skips auto-detection (more reliable)."""
    import speech_recognition as sr
    from faster_whisper.audio import decode_audio

    samples = decode_audio(io.BytesIO(audio))  # 16 kHz mono float32
    if lang in GOOGLE_LOCALES:
        prob = 1.0
    else:
        lang, prob = detect_spoken_language(samples)
    try:
        return Transcript(_google_stt(samples, lang), lang, round(prob, 3), "google")
    except sr.UnknownValueError:
        return Transcript("", lang, round(prob, 3), "google")  # Google heard no words
    except sr.RequestError:
        return Transcript(_whisper_stt(samples, lang), lang, round(prob, 3), "whisper")


# ---------------------------------------------------------------- text → speech

# Natural neural voices (Microsoft Edge read-aloud, free, no key). Female voices: clear and calm for advice.
EDGE_VOICES = {
    "hi": "hi-IN-SwaraNeural", "mr": "mr-IN-AarohiNeural", "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural", "bn": "bn-IN-TanishaaNeural", "gu": "gu-IN-DhwaniNeural",
    "kn": "kn-IN-SapnaNeural", "ml": "ml-IN-SobhanaNeural", "ur": "ur-IN-GulNeural", "en": "en-IN-NeerjaNeural",
}
EDGE_TIMEOUT = 25
EDGE_BREAKER_SECONDS = 60
TTS_CACHE_MAX_BYTES = 150 * 1024 * 1024

_edge_blocked_until = 0.0
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]")


def clean_for_speech(text: str, lang: str = "en") -> str:
    """Remove emoji and list markup that a voice would read out loud as noise."""
    text = _EMOJI.sub("", text)
    text = re.sub(r"^[\s\-\*•]+", "", text, flags=re.MULTILINE)   # "- " list bullets
    if lang == "en":  # other languages' neural voices already read °C and % in their own words
        text = text.replace("°C", " degrees").replace("%", " percent")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{2,}", "\n", text)).strip()


def _tts_cache_path(lang: str, voice: str, text: str):
    key = hashlib.sha1(f"{voice}|{settings.tts_rate}|{text}".encode("utf-8")).hexdigest()
    return settings.cache_dir / "tts" / f"{lang}-{key}.mp3"


def _cache_read(path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def _cache_write(path, data: bytes) -> None:
    try:
        folder = path.parent
        folder.mkdir(parents=True, exist_ok=True)
        if sum(f.stat().st_size for f in folder.glob("*.mp3")) > TTS_CACHE_MAX_BYTES:
            return  # stop growing instead of filling the disk
        path.write_bytes(data)
    except OSError as exc:
        log.warning("could not write voice cache: %s", exc)


async def _edge_stream(text: str, voice: str) -> bytes:
    import edge_tts

    audio = bytearray()
    async for chunk in edge_tts.Communicate(text, voice, rate=settings.tts_rate).stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    return bytes(audio)


def _edge(text: str, lang: str) -> bytes | None:
    """Natural neural voice. None if unavailable (no voice for the language, offline, or recently failing)."""
    global _edge_blocked_until
    voice = EDGE_VOICES.get(lang)
    if voice is None or time.monotonic() < _edge_blocked_until:
        return None
    try:
        data = asyncio.run(asyncio.wait_for(_edge_stream(text, voice), timeout=EDGE_TIMEOUT))
    except Exception as exc:  # network, service change, timeout: fall back, and stop retrying for a minute
        _edge_blocked_until = time.monotonic() + EDGE_BREAKER_SECONDS
        log.warning("neural voice failed (%s): using the basic voice for %ds", type(exc).__name__, EDGE_BREAKER_SECONDS)
        return None
    return data or None


def _gtts(text: str, lang: str) -> bytes | None:
    """Basic (robotic) voice from Google Translate TTS. The backup."""
    from gtts import gTTS
    from gtts.tts import gTTSError

    buf = io.BytesIO()
    try:
        gTTS(text=text, lang=lang).write_to_fp(buf)
    except (gTTSError, OSError, ValueError) as exc:
        log.warning("basic voice failed: %s", type(exc).__name__)
        return None
    return buf.getvalue() or None


def speak(text: str, lang: str) -> bytes | None:
    """MP3 bytes: natural neural voice, else the basic voice, else None (the browser then uses its own voice)."""
    text = clean_for_speech(text, lang)
    if lang not in TTS_LANGS or not text:
        return None
    voice = EDGE_VOICES.get(lang)
    cached = _cache_read(_tts_cache_path(lang, voice, text)) if voice else None
    if cached:
        return cached
    audio = _edge(text, lang)
    if audio:
        _cache_write(_tts_cache_path(lang, voice, text), audio)
        return audio
    return _gtts(text, lang)
