"""Offline tests for language detection, entities, intent, and advice lookup."""

import pytest

from kisanmitra.advice import find_advice
from kisanmitra.entities import extract_entities
from kisanmitra.intent import predict_intent
from kisanmitra.langid import detect_language


@pytest.mark.parametrize("text, lang, script", [
    ("mera tamatar ka paudha peela ho raha hai, kya karu?", "hi", "latin"),
    ("मेरे टमाटर के पत्ते पीले हो रहे हैं", "hi", "native"),
    ("नाशिक मध्ये कांद्याचा भाव काय आहे?", "mr", "native"),
    ("पुण्यात उद्या पाऊस पडेल का?", "mr", "native"),
    ("What is the price of wheat in Indore?", "en", "native"),
    ("కాంద ధర ఎంత", "te", "native"),
])
def test_language_detection(text, lang, script):
    result = detect_language(text)
    assert (result.lang, result.script) == (lang, script)


@pytest.mark.parametrize("text, crop, symptom, location", [
    ("mera tamatar ka paudha peela ho raha hai", "tomato", "yellowing", None),
    ("नाशिक मध्ये कांद्याचा भाव काय आहे?", "onion", None, "Nashik"),
    ("पुण्यात उद्या पाऊस पडेल का?", None, None, "Pune"),
    ("kapas me gulabi sundi lag gayi", "cotton", "pests", None),
    ("dhanyavad", None, None, None),  # must not match "dhan" (paddy)
])
def test_entities(text, crop, symptom, location):
    e = extract_entities(text)
    assert (e.crop, e.symptom, e.location) == (crop, symptom, location)


@pytest.mark.parametrize("text, intent", [
    ("mera tamatar ka paudha peela ho raha hai, kya karu?", "crop_disease"),
    ("नाशिक मध्ये कांद्याचा भाव काय आहे?", "market_price"),
    ("इंदौर में अगले दो दिन बारिश होगी क्या?", "weather"),
    ("What is the price of wheat in Indore?", "market_price"),
    ("will it rain tomorrow in nagpur", "weather"),
    ("namaste", "general"),
])
def test_intent(text, intent):
    assert predict_intent(text)[0] == intent


def test_advice_lookup_falls_back_to_generic():
    assert find_advice("tomato", "yellowing")["crop"] == "tomato"
    assert find_advice("wheat", "rot")["crop"] == "*"
    assert find_advice("tomato", None) is None
