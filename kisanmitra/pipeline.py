"""Glue: language → intent → entities → skill → translate back."""

import time
from dataclasses import dataclass, field

import requests

from kisanmitra import LANG_NAMES, advice, mandi, places, weather
from kisanmitra.entities import Entities, crops, extract_entities, known_words
from kisanmitra.intent import predict_intent
from kisanmitra.langid import detect_language
from kisanmitra.translate import translate, translate_ex

NLU_LANGS = {"hi", "mr", "en"}  # languages the intent model / keyword lists are trained on
LOW_CONFIDENCE = 0.45
FOLLOW_UP_CONFIDENCE = 0.60   # below this, a short question may be a follow-up to the previous topic
FOLLOW_UP_MAX_WORDS = 6
FOLLOW_UP_INTENTS = ("weather", "market_price")
REQUIRED_SLOTS = {"crop_disease": ("crop", "symptom"), "market_price": ("crop",), "weather": ("location",)}
HELPLINE = "For confirmation, call the Kisan Call Centre at 1800-180-1551 (free) or visit your nearest Krishi Vigyan Kendra."
SCHEME_WORDS = ("pm kisan", "pm-kisan", "पीएम किसान", "पीएम-किसान", "yojana", "योजना", "scheme")


@dataclass
class Reply:
    text: str                       # final reply in the user's language
    english: str                    # the same reply in English (before translation)
    lang: str
    script: str
    intent: str
    confidence: float
    entities: dict
    details: dict = field(default_factory=dict)
    spoken: str | None = None       # short version for text-to-speech (voice mode only)


# ---------- skill handlers (all return English text) ----------

def _crop_disease(ents: Entities, place: places.Place | None, details: dict) -> str:
    if not ents.crop and not ents.symptom:
        return "Please tell me the crop name and the problem you see, for example: yellow leaves, spots, insects, wilting, curling or rotting. You can also send a photo of the leaf."
    crop_name = crops()[ents.crop]["en"] if ents.crop else "your crop"
    if not ents.symptom:
        return f"What problem do you see on {crop_name}? For example: yellow leaves, spots, insects, wilting, curling or rotting."
    entry = advice.find_advice(ents.crop, ents.symptom)
    details["advice_entry"] = entry
    if not entry:
        return f"I don't have advice for this problem yet. {HELPLINE}"
    first_step = entry["advice"].split(". ")[0].rstrip(".")
    details["speech"] = f"Possible problem in {crop_name}: {entry['problem']}. {first_step}. Full advice is on the screen."
    return f"Possible problem in {crop_name}: {entry['problem']}.\nWhat to do: {entry['advice']}\n{HELPLINE}"


def _ago(ts: float) -> str:
    hours = max(1, round((time.time() - ts) / 3600))
    return f"{hours} hour{'s' if hours != 1 else ''}" if hours < 48 else f"{round(hours / 24)} days"


def _market_price(ents: Entities, place: places.Place | None, details: dict) -> str:
    if not ents.crop:
        return "Which crop's price do you want? For example: onion, tomato, wheat, soybean or cotton."
    crop = crops()[ents.crop]
    district = (place.district or place.name) if place else None
    state = place.mandi_state if place else None
    result = mandi.get_prices(crop["agmarknet"], district=district, state=state)
    details["mandi"] = {
        "source": result.source, "scope": result.scope, "error": result.error,
        "records": result.records, "fetched_at": result.fetched_at,
    }
    if not result.records:
        return f"No mandi price for {crop['en']} has been reported today. Please try again tomorrow."

    lines = []
    if result.source == "sample":
        lines.append("(Live mandi data is unavailable right now. These are SAMPLE prices for demonstration only.)")
    elif result.source == "cached" and result.fetched_at:
        lines.append(f"(Live mandi data is unavailable right now. These prices were saved {_ago(result.fetched_at)} ago.)")
    if place and result.scope != "district":
        where = place.state if result.scope == "state" else "India"
        lines.append(f"No report from {place.district or place.name} today, so here are other markets in {where}.")
    date = result.records[0].get("arrival_date", "")
    lines.append(f"{crop['en'].capitalize()} prices" + (f" ({date})" if date and date != "sample" else "") + ", per quintal:")
    top = result.records[0]
    details["speech"] = (f"{crop['en'].capitalize()} price in {top['market']} market is "
                         f"{float(top['modal_price']):,.0f} rupees per quintal.")
    if result.source != "live":
        details["speech"] = ("These are sample prices. " if result.source == "sample" else "These are saved prices. ") + details["speech"]
    for r in result.records[:3]:
        lines.append(
            f"- {r['market']} ({r['district']}): Rs {float(r['modal_price']):,.0f} "
            f"(min Rs {float(r['min_price']):,.0f}, max Rs {float(r['max_price']):,.0f})"
        )
    return "\n".join(lines)


def _weather(ents: Entities, place: places.Place | None, details: dict) -> str:
    if place is None:
        details["needs_location"] = True
        return ("Which village or town do you want the weather for? Tell me the name, "
                "or tap the location button to use your current location.")
    located = places.ensure_coordinates(place)
    if located is None:
        return f"I could not find the place {place.name}. Please try the nearest town, or use your current location."
    try:
        fc = weather.forecast(located.lat, located.lon)
    except (weather.WeatherError, requests.RequestException, KeyError, ValueError):
        details["weather_error"] = True  # the cause is in the server log (never sent to the browser)
        return "The weather service is not reachable right now. Please try again in a few minutes."
    days = fc.days
    label = located.label()
    details["weather"] = {
        "place": label,
        "source": fc.source,
        "station": fc.station,
        "current": fc.current.__dict__ if fc.current else None,
        "days": [d.__dict__ for d in days],
    }
    lines = [f"Weather for {label}:"]
    if fc.current:
        c = fc.current
        feels = f" (feels like {c.feels_like:.0f})" if c.feels_like is not None and abs(c.feels_like - c.temp) >= 2 else ""
        lines.append(f"Now: {c.temp:.0f} degrees C{feels}, {c.description.lower()}, humidity {c.humidity}%, wind {c.wind_kmh:.0f} km/h")
    lines.append(f"Next {len(days)} days:")
    for d in days:
        lines.append(
            f"- {d.day.strftime('%d %b')}: {d.t_min:.0f} to {d.t_max:.0f} degrees C, "
            f"{d.description.lower()}, rain {d.rain_mm:.1f} mm ({d.rain_chance}% chance)"
        )
    tips = weather.farming_tips(days, fc.current)
    lines += [f"Tip: {t}" for t in tips]
    nxt = days[1] if len(days) > 1 else days[0]
    now = f"Now {fc.current.temp:.0f} degrees. " if fc.current else ""
    details["speech"] = (f"{now}Tomorrow in {located.name}: up to {nxt.t_max:.0f} degrees, "
                         f"{nxt.rain_chance} percent chance of rain. {tips[0]}")
    return "\n".join(lines)


def _general(text: str) -> str:
    if any(w in text.lower() for w in SCHEME_WORDS):
        return ("PM-KISAN gives eligible farmer families Rs 6,000 per year in three instalments of Rs 2,000, "
                "paid directly to the bank account. Check your status or register at pmkisan.gov.in, "
                "or call the PM-KISAN helpline 155261.")
    return ("Namaste! I am KisanMitra, your farming friend. Ask me about crop problems "
            "(for example: yellow leaves on tomato), mandi prices (onion price in Nashik), "
            "or weather (will it rain in Pune?).")


HANDLERS = {"crop_disease": _crop_disease, "market_price": _market_price, "weather": _weather}


def _resolve_place(
    intent: str,
    ents: Entities,
    texts: list[str],
    saved: places.Place | None,
    default_location: str | None,
    details: dict,
) -> places.Place | None:
    """Which place is this question about? Named in the question > saved/GPS location > nothing."""
    if intent not in ("weather", "market_price"):
        return saved
    if ents.location:
        details["place_from"] = "question"
        return places.from_gazetteer(ents.location)
    for t in texts:  # any village/town named in the question, e.g. "will it rain in Satana"
        guessed = places.guess_from_text(t, set(known_words()))
        if guessed:
            details["place_from"] = "question"
            return guessed
    if saved:
        details["place_from"] = "saved"
        return saved
    if default_location:  # older clients that only send a city name
        details["place_from"] = "saved"
        return places.from_gazetteer(default_location)
    return None


# ---------- main entry ----------

def _missing_slots(intent: str, ents: Entities) -> bool:
    return any(getattr(ents, slot) is None for slot in REQUIRED_SLOTS.get(intent, ()))


def _word_count(text: str) -> int:
    return len(text.split())


def respond(
    text: str,
    lang_pref: str = "auto",
    default_location: str | None = None,
    voice: bool = False,
    speech_lang: str | None = None,
    place: places.Place | None = None,
    context: dict | None = None,
) -> Reply:
    """`place`: the farmer's saved/GPS location. `context`: the previous topic, e.g. {"intent": "market_price", "crop": "onion"}."""
    detected = detect_language(text)
    # Hindi vs Marathi can't always be told apart from a (possibly misspelled)
    # transcript; the language Whisper heard in the audio is the better signal.
    if speech_lang in ("hi", "mr") and detected.lang in ("hi", "mr"):
        detected.lang = speech_lang
    lang = detected.lang if lang_pref == "auto" else lang_pref
    script = detected.script if detected.lang == lang else "native"

    # Languages outside the trained set are translated to English for understanding.
    nlu_text = text if detected.lang in NLU_LANGS else translate(text, "en", source="auto")

    intent, conf = predict_intent(nlu_text)
    first_intent, first_conf = intent, conf  # before any retry: how clear was the question as asked?
    ents = extract_entities(nlu_text)
    details: dict = {"nlu_text": nlu_text}
    texts = [nlu_text]

    # Fallback: if the model is unsure or a needed entity is missing (often a spelling
    # variant, e.g. from speech-to-text), also try the English translation of the query.
    if nlu_text == text and detected.lang != "en" and (conf < LOW_CONFIDENCE or _missing_slots(intent, ents)):
        english_query = translate(text, "en", source="auto")
        en_intent, en_conf = predict_intent(english_query)
        if en_conf > conf:
            intent, conf = en_intent, en_conf
        en_ents = extract_entities(english_query)
        for slot in ("crop", "symptom", "location"):
            if getattr(ents, slot) is None:
                setattr(ents, slot, getattr(en_ents, slot))
        details["english_fallback"] = english_query
        texts.append(english_query)

    if conf < LOW_CONFIDENCE and ents.symptom:
        intent = "crop_disease"

    # Follow-up questions: "aur Pune me?" after a price question means "and the price in Pune?".
    ctx = context or {}
    is_short = _word_count(nlu_text) <= FOLLOW_UP_MAX_WORDS
    unclear = first_intent == "general" or first_conf < FOLLOW_UP_CONFIDENCE
    if ctx.get("intent") in FOLLOW_UP_INTENTS and is_short and unclear and (ents.location or ents.crop):
        intent = ctx["intent"]
        details["follow_up"] = True
    if intent == "market_price" and not ents.crop and ctx.get("crop") and ctx.get("intent") == "market_price":
        ents.crop = ctx["crop"]
        details["follow_up"] = True

    resolved = _resolve_place(intent, ents, texts, place, default_location, details)
    if resolved is not None:
        if intent in ("weather", "market_price") and not ents.location:
            ents.location = resolved.name
        details["place"] = resolved.to_dict()

    handler = HANDLERS.get(intent)
    english = handler(ents, resolved, details) if handler else _general(nlu_text)

    reply = english
    if lang != "en":
        reply, translated = translate_ex(english, lang, romanize=(script == "latin"))
        if not translated:  # every free translation service failed: the farmer gets English, and the UI says why
            details["translation_failed"] = True
    spoken = None
    if voice:  # speech engines pronounce native script best, so never romanize here
        short = details.get("speech", english)
        spoken = short if lang == "en" else translate(short, lang)
    return Reply(
        text=reply, english=english, lang=lang, script=script, intent=intent,
        confidence=round(conf, 3), entities=ents.as_dict(), details=details, spoken=spoken,
    )


def describe_language(reply: Reply) -> str:
    name = LANG_NAMES.get(reply.lang, reply.lang)
    return f"{name} (romanized)" if reply.script == "latin" else name
