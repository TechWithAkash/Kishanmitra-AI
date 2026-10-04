"""KisanMitra AI — multilingual NLP advisory assistant for farmers (MVP)."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

LANG_NAMES = {
    "hi": "Hindi", "mr": "Marathi", "en": "English", "bn": "Bengali", "pa": "Punjabi",
    "gu": "Gujarati", "or": "Odia", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam", "ur": "Urdu",
}
