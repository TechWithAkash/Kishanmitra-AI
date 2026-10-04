import type { BotReply, ChatContext, Heard, Place, VoiceResult } from "./types";

export class ApiError extends Error {}

async function request(path: string, init: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(
      "Cannot reach the KisanMitra server. Is the backend running on port 8000?",
    );
  }
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json()).detail ?? "";
    } catch {}
    throw new ApiError(detail || `Server error (${res.status})`);
  }
  return res;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function audioForm(blob: Blob, langPref: string) {
  const form = new FormData();
  form.append("audio", blob, "speech.webm");
  form.append("lang_pref", langPref);
  return form;
}

/** Only the fields the backend needs (the saved place may carry display-only extras). */
const placeBody = (p: Place | null) =>
  p ? { name: p.name, lat: p.lat, lon: p.lon, state: p.state, district: p.district } : null;

export async function chat(
  text: string,
  langPref: string,
  place: Place | null,
  context?: ChatContext | null,
): Promise<BotReply> {
  const res = await request("/chat", json({ text, lang_pref: langPref, place: placeBody(place), context }));
  return res.json();
}

export async function voice(
  blob: Blob,
  langPref: string,
  place: Place | null,
  context?: ChatContext | null,
): Promise<VoiceResult> {
  const form = audioForm(blob, langPref);
  if (place) form.append("place", JSON.stringify(placeBody(place)));
  if (context) form.append("context", JSON.stringify(context));
  const res = await request("/voice", { method: "POST", body: form });
  return res.json();
}

export async function searchPlaces(q: string, signal?: AbortSignal): Promise<Place[]> {
  const res = await request(`/places/search?q=${encodeURIComponent(q)}`, { method: "GET", signal });
  return res.json();
}

export async function reversePlace(lat: number, lon: number): Promise<Place> {
  const res = await request(`/places/reverse?lat=${lat}&lon=${lon}`, { method: "GET" });
  return res.json();
}

export async function diagnose(
  image: Blob,
  langPref: string,
  location: string | null,
  text?: string,
  crop?: string,
): Promise<BotReply> {
  const form = new FormData();
  form.append("image", image, "crop.jpg");
  form.append("lang_pref", langPref);
  if (location) form.append("location", location);
  if (text) form.append("text", text);
  if (crop && crop !== "any") form.append("crop", crop);
  const res = await request("/diagnose", { method: "POST", body: form });
  return res.json();
}

export async function transcribe(blob: Blob, langPref: string): Promise<Heard> {
  const res = await request("/transcribe", { method: "POST", body: audioForm(blob, langPref) });
  return res.json();
}

/** Speak `text` aloud. Pass `fromEnglish` when `text` is English and should be translated first. */
export async function tts(text: string, lang: string, fromEnglish = false): Promise<Blob> {
  const res = await request("/tts", json({ text, lang, from_english: fromEnglish }));
  return res.blob();
}

