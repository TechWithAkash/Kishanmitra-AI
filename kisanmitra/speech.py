"""Voice in / voice out — all free.

Speech → text is a two-step hybrid:
  1. Whisper (faster-whisper, runs locally) DETECTS which language is spoken, so the
     farmer never has to pick a language. Whisper is reliable at this.
  2. Google's free speech recognition WRITES OUT the words in that language. It is far
     more accurate than small Whisper for Indian languages like Telugu and Bengali.
     If Google is unreachable, Whisper's own transcript is used instead.
The Whisper model downloads once (~500 MB for "small"); change with WHISPER_MODEL.

Text → speech: gTTS (free Google TTS, no key).
"""

import io
import os
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

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


def speak(text: str, lang: str) -> bytes | None:
    """MP3 bytes, or None if the language isn't supported or gTTS is unreachable."""
    if lang not in TTS_LANGS or not text.strip():
        return None
    from gtts import gTTS
    from gtts.tts import gTTSError

    buf = io.BytesIO()
    try:
        gTTS(text=text, lang=lang).write_to_fp(buf)
    except (gTTSError, OSError):
        return None
    return buf.getvalue()
