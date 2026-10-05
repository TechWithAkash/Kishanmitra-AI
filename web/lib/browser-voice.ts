import type { Playback } from "./audio";

const BCP47: Record<string, string> = {
  hi: "hi-IN", mr: "mr-IN", ta: "ta-IN", te: "te-IN", bn: "bn-IN", gu: "gu-IN",
  kn: "kn-IN", ml: "ml-IN", pa: "pa-IN", ur: "ur-IN", en: "en-IN",
};

function loadVoices(): Promise<SpeechSynthesisVoice[]> {
  const now = speechSynthesis.getVoices();
  if (now.length) return Promise.resolve(now);
  return new Promise((resolve) => {
    const finish = () => resolve(speechSynthesis.getVoices());
    speechSynthesis.addEventListener("voiceschanged", finish, { once: true });
    setTimeout(finish, 1500); // some browsers never fire the event
  });
}

/** Prefer a high-quality voice for the exact language ("Google …", "Natural", "Enhanced"). */
function pickVoice(voices: SpeechSynthesisVoice[], lang: string): SpeechSynthesisVoice | null {
  const tag = (BCP47[lang] ?? lang).toLowerCase();
  const norm = (v: SpeechSynthesisVoice) => v.lang.toLowerCase().replace("_", "-");
  const matches = voices.filter((v) => norm(v) === tag || norm(v).startsWith(`${lang}-`));
  return (
    matches.find((v) => /google|neural|natural|enhanced|premium/i.test(v.name)) ?? matches[0] ?? null
  );
}

/**
 * Speak with the device's own built-in voice (works offline, nothing to download). This is the
 * safety net when the server's natural voice is unavailable or the browser blocks its audio.
 * `started` is false when the device has no voice for the language: we never read Hindi with an
 * English voice, because that sounds like gibberish.
 */
export function speakWithBrowser(text: string, lang: string): Playback {
  let finish!: () => void;
  const done = new Promise<void>((r) => (finish = r));
  let begin!: (ok: boolean) => void;
  const started = new Promise<boolean>((r) => (begin = r));
  const fail = () => {
    begin(false);
    finish();
  };

  if (typeof speechSynthesis === "undefined" || typeof SpeechSynthesisUtterance === "undefined" || !text.trim()) {
    fail();
    return { done, started, stop: () => {} };
  }

  void loadVoices().then((voices) => {
    const voice = pickVoice(voices, lang);
    if (!voice) {
      console.warn(`No built-in voice for "${lang}" on this device`);
      return fail();
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.rate = 0.92; // a little slower is clearer
    utterance.onstart = () => begin(true);
    utterance.onend = () => finish();
    utterance.onerror = (e) => {
      console.warn("Built-in voice failed:", e.error);
      fail();
    };
    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
  });

  return {
    done,
    started,
    stop: () => {
      if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
      finish();
    },
  };
}
