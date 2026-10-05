"""Photo of a crop → diagnosis reply, in the farmer's language."""

import json
from dataclasses import asdict
from functools import lru_cache

from kisanmitra import DATA_DIR, vision
from kisanmitra.entities import Entities, crops, extract_entities
from kisanmitra.pipeline import HELPLINE, Reply
from kisanmitra.translate import translate_ex

CONFIDENT = 0.75   # at or above (and clearly ahead of the runner-up): report as the diagnosis
MARGIN = 0.30      # lead over the 2nd guess needed to call it confident
POSSIBLE = 0.40    # at or above: report as a possibility; below: "not sure"

SUPPORTED_CROPS = "tomato, potato, maize (corn), pepper, grape, apple, peach, cherry, strawberry, squash and orange"
NOT_SURE = (
    "I am not sure what is wrong with this plant from the photo. For a better result, take a clear, "
    "close-up photo of ONE affected leaf in daylight, with the leaf filling most of the picture. "
    f"This photo check works best for: {SUPPORTED_CROPS}. For other crops, tell me the problem in words instead."
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


def diagnose(
    image_bytes: bytes,
    lang: str = "en",
    location: str | None = None,
    crop: str | None = None,
    text: str | None = None,
) -> Reply:
    """`crop` is what the farmer says the plant is. If they did not pick one, a crop named in `text` is used."""
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
