"""Photo of a crop → diagnosis reply, in the farmer's language.

Order of attempts:
  1. An AI vision model (Gemini / Claude, see vision_llm.py): any crop, any plant part.
  2. If no AI key is set, or the AI call fails: the small local leaf model (vision.py), which only
     understands single leaves of a few crops, and says so when it is unsure.
  3. If that is unsure but the farmer also described the problem in words, answer from the description.
"""

import json
import logging
from dataclasses import asdict
from functools import lru_cache

from kisanmitra import DATA_DIR, vision, vision_llm
from kisanmitra.config import redact
from kisanmitra.entities import Entities, crops, extract_entities
from kisanmitra.pipeline import HELPLINE, Reply, respond
from kisanmitra.translate import translate_ex

log = logging.getLogger("kisanmitra.diagnosis")

CONFIDENT = 0.75   # at or above (and clearly ahead of the runner-up): report as the diagnosis
MARGIN = 0.30      # lead over the 2nd guess needed to call it confident
POSSIBLE = 0.40    # at or above: report as a possibility; below: "not sure"

SUPPORTED_CROPS = "tomato, potato, maize (corn), pepper, grape, apple, peach, cherry, strawberry, squash and orange"
NOT_SURE = (
    "I am not sure what is wrong with this plant from the photo. This basic photo check only understands "
    "single LEAVES (not fruits, stems or whole plants). For a better result, take a clear, close-up photo of "
    f"ONE affected leaf in daylight. It works best for: {SUPPORTED_CROPS}. For anything else, tell me the problem in words."
)


def _unsupported_crop_message(crop_name: str) -> str:
    return (
        f"I cannot check {crop_name} from a photo yet: the photo check works for {SUPPORTED_CROPS}. "
        f"Please tell me the problem in words, for example: yellow leaves, spots, insects, wilting. {HELPLINE}"
    )


@lru_cache(maxsize=1)
def _advice() -> dict:
    with open(DATA_DIR / "image_advice.json", encoding="utf-8") as f:
        return json.load(f)


def _describe(label: str, confidence: float, sure: bool) -> tuple[str, dict]:
    """English answer for one predicted label, plus the matched advice entry ({} if none)."""
    entry = _advice().get(label)
    pct = round(confidence * 100)
    if entry is None:
        return (
            f"The photo looks like: {label} ({pct}% sure). I do not have detailed advice for this yet. {HELPLINE}",
            {},
        )
    if entry.get("healthy"):
        return f"Good news: this {entry['crop']} leaf looks healthy ({pct}% sure).\n{entry['advice']}", entry
    opener = "Your plant has" if sure else "Your plant may have"
    return (
        f"{opener} {entry['name']} in {entry['crop']} ({pct}% sure).\nWhat to do: {entry['advice']}\n{HELPLINE}",
        entry,
    )


_CONFIDENCE_STATUS = {"high": "confident", "medium": "possible", "low": "unsure"}
_CONFIDENCE_NUMBER = {"high": 0.9, "medium": 0.6, "low": 0.3}


def _diagnose_ai(image_bytes: bytes, lang: str, location: str | None, text: str | None) -> Reply:
    d = vision_llm.analyse(image_bytes, lang, note=text, region=location)

    translated = True
    if lang == "en":
        reply_text = d.reply_en
    elif d.reply_text:          # written by the AI in the farmer's language, numbers already checked
        reply_text = d.reply_text
    else:                       # unsafe or missing: translate the sanitized English instead
        reply_text, translated = translate_ex(d.reply_en, lang)

    status = "unsure" if d.part == "not_a_plant" else _CONFIDENCE_STATUS[d.confidence]
    number = _CONFIDENCE_NUMBER[d.confidence]
    crop_id = extract_entities(d.plant).crop if d.plant else None
    label = f"Healthy {d.plant}" if d.healthy and d.plant else (d.problem or "Unclear")
    details = {
        "vision": {
            "status": status,
            "engine": d.engine,
            "plant": d.plant,
            "part": d.part,
            "problem": d.problem,
            "category": d.category,
            "healthy": d.healthy,
            "confidence_label": d.confidence,
            "symptoms": d.symptoms,
            "see_expert": d.see_expert,
            "predictions": [{"label": label, "confidence": number, "crop": crop_id, "healthy": d.healthy}],
        }
    }
    if not translated:
        details["translation_failed"] = True
    return Reply(
        text=reply_text, english=d.reply_en, lang=lang, script="native", intent="crop_image", confidence=number,
        entities=asdict(Entities(crop=crop_id or d.plant, location=location)), details=details,
    )


def _from_description(text: str, lang: str, location: str | None) -> Reply | None:
    """The photo was not understood, but the farmer also wrote what is wrong: answer from those words."""
    reply = respond(text, lang_pref=lang, only_intents=("crop_disease",))
    if reply is None or not reply.details.get("advice_entry"):
        return None
    note_en = "I could not judge the photo itself, so this answer is based on what you wrote."
    note, ok = translate_ex(note_en, lang)
    details = {k: v for k, v in reply.details.items() if k != "translation_failed"}
    if not ok or reply.details.get("translation_failed"):
        details["translation_failed"] = True
    return Reply(
        text=f"{note}\n{reply.text}", english=f"{note_en}\n{reply.english}", lang=lang, script=reply.script,
        intent="crop_disease", confidence=reply.confidence, entities=reply.entities, details=details,
    )


def diagnose(
    image_bytes: bytes,
    lang: str = "en",
    location: str | None = None,
    crop: str | None = None,
    text: str | None = None,
) -> Reply:
    if vision_llm.provider():
        try:
            return _diagnose_ai(image_bytes, lang, location, text)
        except vision_llm.VisionLLMError as exc:
            log.warning("AI photo check failed, falling back to the local leaf model: %s", redact(str(exc)))

    reply = _diagnose_local(image_bytes, lang, location, crop, text)
    if reply.details["vision"]["status"] in ("unsure", "unsupported") and text and text.strip():
        described = _from_description(text, lang, location)
        if described:
            return described
    return reply


def _diagnose_local(
    image_bytes: bytes,
    lang: str,
    location: str | None,
    crop: str | None,
    text: str | None,
) -> Reply:
    """The small local leaf model. `crop` is what the farmer says it is; if not given, a crop named in `text` is used."""
    crop = crop or (extract_entities(text).crop if text else None)

    # The photo model only knows some crops. If the farmer names another one, say so
    # instead of forcing the photo into the nearest wrong class.
    if crop and crop not in vision.supported_crops():
        name = crops().get(crop, {}).get("en", crop)
        english = _unsupported_crop_message(name)
        reply_text, translated = translate_ex(english, lang)
        return Reply(
            text=reply_text, english=english, lang=lang, script="native", intent="crop_image", confidence=0.0,
            entities=asdict(Entities(crop=crop, location=location)),
            details={"vision": {"status": "unsupported", "predictions": []}, **({} if translated else {"translation_failed": True})},
        )

    preds = vision.classify(image_bytes, top_k=3, crop=crop)
    top = preds[0]
    lead = top.confidence - (preds[1].confidence if len(preds) > 1 else 0.0)

    if top.confidence < POSSIBLE:
        english, entry, status = NOT_SURE, {}, "unsure"
    else:
        english, entry = _describe(top.label, top.confidence, sure=top.confidence >= CONFIDENT and lead >= MARGIN)
        status = "confident" if top.confidence >= CONFIDENT and lead >= MARGIN else "possible"

    advice = _advice()
    details = {
        "vision": {
            "status": status,
            "predictions": [
                {
                    "label": p.label,
                    "confidence": p.confidence,
                    "crop": advice.get(p.label, {}).get("crop"),
                    "healthy": bool(advice.get(p.label, {}).get("healthy")),
                }
                for p in preds
            ],
        }
    }
    reply_text, translated = translate_ex(english, lang)
    if not translated:
        details["translation_failed"] = True
    return Reply(
        text=reply_text,
        english=english,
        lang=lang,
        script="native",
        intent="crop_image",
        confidence=top.confidence,
        entities=asdict(Entities(crop=crop or (entry.get("crop") if status != "unsure" else None), location=location)),
        details=details,
    )
