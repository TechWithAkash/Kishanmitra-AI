"""FastAPI backend used by the Next.js frontend (web/).

Run: uv run uvicorn kisanmitra.server:app --port 8000
"""

import base64
import logging
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError

from kisanmitra import diagnosis, places, speech, vision
from kisanmitra.config import settings
from kisanmitra.entities import locations
from kisanmitra.guards import RateLimiter, client_ip
from kisanmitra.langid import detect_language
from kisanmitra.pipeline import Reply, respond
from kisanmitra.translate import translate

VERSION = "1.0.0"
log = logging.getLogger("kisanmitra.api")
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

MAX_BYTES = settings.max_upload_mb * 1024 * 1024
HEAVY_PATHS = {"/api/voice", "/api/diagnose", "/api/transcribe", "/api/tts"}

normal_limiter = RateLimiter(settings.rate_limit_per_min)
heavy_limiter = RateLimiter(settings.heavy_rate_limit_per_min)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Load the speech and photo models in the background so the first request isn't slow.
    threading.Thread(target=speech._whisper, daemon=True).start()
    threading.Thread(target=vision._load, daemon=True).start()
    yield


app = FastAPI(title="KisanMitra AI", version=VERSION, lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["GET", "POST"], allow_headers=["*"]
    )


@app.middleware("http")
async def guard(request: Request, call_next):
    """Request id + access log, rate limit, upload size limit, and a JSON 500 instead of a stack trace."""
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    path = request.url.path

    if path.startswith("/api/") and path != "/api/health":
        limiter = heavy_limiter if path in HEAVY_PATHS else normal_limiter
        wait = limiter.check(client_ip(request, settings.trust_proxy))
        if wait is not None:
            return JSONResponse(
                {"detail": "Too many requests. Please wait a moment and try again."},
                status_code=429,
                headers={"Retry-After": str(int(wait))},
            )
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BYTES + 1024 * 1024:
            return JSONResponse({"detail": f"Upload too large (max {settings.max_upload_mb} MB)"}, status_code=413)

    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled error rid=%s %s %s", rid, request.method, path)
        response = JSONResponse({"detail": "Something went wrong on the server. Please try again."}, status_code=500)

    response.headers["X-Request-ID"] = rid
    response.headers["X-Content-Type-Options"] = "nosniff"
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    log.info(
        "%s %s %s %.0fms ip=%s rid=%s",
        request.method, path, response.status_code, (time.perf_counter() - started) * 1000,
        client_ip(request, settings.trust_proxy), rid,
    )
    return response


# ---------------------------------------------------------------- request models

class PlaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    state: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)

    def to_place(self) -> places.Place:
        return places.Place(self.name, self.lat, self.lon, self.state, self.district, "saved")


class ContextIn(BaseModel):
    """What the previous answer was about, so "aur Pune me?" can be understood."""
    intent: str | None = Field(default=None, max_length=30)
    crop: str | None = Field(default=None, max_length=30)


class ChatRequest(BaseModel):
    text: str = Field(max_length=settings.max_text_chars)
    lang_pref: str = Field(default="auto", max_length=10)
    location: str | None = Field(default=None, max_length=80)   # older clients: just a city name
    place: PlaceIn | None = None
    context: ContextIn | None = None


class TTSRequest(BaseModel):
    text: str = Field(max_length=5000)
    lang: str = Field(max_length=10)
    from_english: bool = False   # text is English: translate to `lang` first (best TTS quality)


def _reply_json(reply: Reply) -> dict:
    data = asdict(reply)
    data["details"].pop("speech", None)  # pipeline internals the UI doesn't need
    return jsonable_encoder(data)


def _clean(value: str | None) -> str | None:
    return None if value in (None, "", "auto", "none") else value


def _parse_form_json(model: type[BaseModel], raw: str | None, field: str):
    if not raw:
        return None
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(422, f"Invalid {field}") from exc


def _read_upload(upload: UploadFile) -> bytes:
    data = upload.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"Upload too large (max {settings.max_upload_mb} MB)")
    return data


# ---------------------------------------------------------------- endpoints
# Endpoints are plain `def` (not `async def`): they do slow, blocking work (models, network),
# so FastAPI runs them in a thread pool instead of freezing the event loop.

@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "version": VERSION,
        "whisper_loaded": speech._whisper.cache_info().currsize > 0,
        "photo_model_loaded": vision._load.cache_info().currsize > 0,
    }


@app.get("/api/locations")
def get_locations() -> list[str]:
    return sorted(locations())


@app.get("/api/places/search")
def search_places(q: str = Query(min_length=2, max_length=80), lang: str = Query("en", max_length=5)) -> list[dict]:
    """Search any village, town or district in India by name."""
    return [p.to_dict() for p in places.search(q, limit=8, language=lang if lang in ("en", "hi", "mr") else "en")]


@app.get("/api/places/reverse")
def reverse_place(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)) -> dict:
    """GPS coordinates → nearest village/town, district and state."""
    return places.reverse(lat, lon).to_dict()


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Empty message")
    reply = respond(
        text,
        lang_pref=req.lang_pref,
        default_location=_clean(req.location),
        place=req.place.to_place() if req.place else None,
        context=req.context.model_dump() if req.context else None,
    )
    return _reply_json(reply)


@app.post("/api/voice")
def voice(
    audio: UploadFile = File(...),
    lang_pref: str = Form("auto"),
    location: str | None = Form(None),
    place: str | None = Form(None),
    context: str | None = Form(None),
) -> dict:
    data = _read_upload(audio)
    if len(data) < 1000:
        raise HTTPException(400, "Audio too short")
    place_in = _parse_form_json(PlaceIn, place, "place")
    context_in = _parse_form_json(ContextIn, context, "context")
    try:
        heard = speech.transcribe(data, lang=_clean(lang_pref))
    except Exception as exc:  # undecodable audio etc.
        log.warning("could not read audio: %s", exc)
        raise HTTPException(400, "Could not read that audio. Please try again.") from exc
    if not heard.text:
        return {"transcript": "", "heard": asdict(heard), "reply": None}

    reply = respond(
        heard.text,
        lang_pref=lang_pref,
        default_location=_clean(location),
        voice=True,
        speech_lang=heard.lang,
        place=place_in.to_place() if place_in else None,
        context=context_in.model_dump() if context_in else None,
    )
    reply.details["heard"] = asdict(heard)
    audio_reply = speech.speak(reply.spoken, reply.lang)
    out = _reply_json(reply)
    out.update(
        transcript=heard.text,
        heard=asdict(heard),
        audio_b64=base64.b64encode(audio_reply).decode() if audio_reply else None,
    )
    return out


@app.post("/api/diagnose")
def diagnose_photo(
    image: UploadFile = File(...),
    lang_pref: str = Form("auto"),
    location: str | None = Form(None),
    text: str | None = Form(None),
    crop: str | None = Form(None),
) -> dict:
    """Crop photo → disease diagnosis, in the farmer's language.

    Reply language: the chosen language, else the language of the optional caption
    typed with the photo, else English.
    """
    text = text[: settings.max_text_chars] if text else text
    lang = _clean(lang_pref) or (detect_language(text).lang if text and text.strip() else "en")
    try:
        reply = diagnosis.diagnose(_read_upload(image), lang, _clean(location), crop=_clean(crop), text=text)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _reply_json(reply)


@app.post("/api/transcribe")
def transcribe(audio: UploadFile = File(...), lang_pref: str = Form("auto")) -> dict:
    """Dictation: speech → text only (no answer)."""
    data = _read_upload(audio)
    if len(data) < 1000:
        raise HTTPException(400, "Audio too short")
    try:
        heard = speech.transcribe(data, lang=_clean(lang_pref))
    except Exception as exc:
        log.warning("could not read audio: %s", exc)
        raise HTTPException(400, "Could not read that audio. Please try again.") from exc
    return asdict(heard)


@app.post("/api/tts")
def tts(req: TTSRequest) -> Response:
    text = translate(req.text, req.lang) if req.from_english and req.lang != "en" else req.text
    mp3 = speech.speak(text, req.lang)
    if mp3 is None:
        raise HTTPException(422, "Text-to-speech is not available for this language right now")
    return Response(mp3, media_type="audio/mpeg")
