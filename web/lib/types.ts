export type Entities = {
  crop: string | null;
  symptom: string | null;
  location: string | null;
};

export type MandiRecord = {
  state: string;
  district: string;
  market: string;
  commodity: string;
  modal_price: number | string;
  min_price: number | string;
  max_price: number | string;
  arrival_date?: string;
};

export type DayForecast = {
  day: string; // ISO date
  t_min: number;
  t_max: number;
  rain_mm: number;
  rain_chance: number;
  wind_kmh: number;
  code: number; // WMO weather code
  description: string;
};

export type CurrentWeather = { temp: number; humidity: number; wind_kmh: number; code: number; description: string };

/** Where the farmer is: from GPS, from search, or named in a question. */
export type Place = {
  name: string;
  lat: number | null;
  lon: number | null;
  state: string | null;
  district: string | null;
  source?: string;
  label?: string;
};

export type ChatContext = { intent: string | null; crop: string | null };

export type VisionPrediction = { label: string; confidence: number; crop: string | null; healthy: boolean };

export type Heard = { text: string; lang: string; lang_prob: number; engine: string };

export type Details = {
  nlu_text?: string;
  location_from?: string | null;
  english_fallback?: string;
  mandi?: {
    source: "live" | "cached" | "sample";
    scope: string;
    error: string | null;
    records: MandiRecord[];
    fetched_at: number | null; // unix seconds
  };
  weather?: { place: string; current: CurrentWeather | null; days: DayForecast[] };
  place?: Place & { label: string };
  place_from?: "question" | "saved";
  needs_location?: boolean;
  follow_up?: boolean;
  advice_entry?: { crop: string; symptom: string; problem: string; advice: string } | null;
  heard?: Heard;
  vision?: { status: "confident" | "possible" | "unsure" | "unsupported"; predictions: VisionPrediction[] };
};

export type BotReply = {
  text: string; // answer in the user's language/script
  english: string;
  lang: string;
  script: "native" | "latin";
  intent: string;
  confidence: number;
  entities: Entities;
  details: Details;
};

export type VoiceResult =
  | { transcript: ""; heard: Heard; reply: null }
  | (BotReply & { transcript: string; heard: Heard; audio_b64: string | null });

export type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  voice?: boolean; // typed vs spoken
  /** Small preview (data URL) of the crop photo the farmer sent. */
  image?: string;
  ts?: number;
  reply?: BotReply;
  error?: boolean;
  /** Only held in memory (too big for localStorage). */
  audioB64?: string | null;
};

export type Chat = {
  id: string;
  title: string;
  createdAt: number;
  messages: Message[];
};
