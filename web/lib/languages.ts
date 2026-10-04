export const LANGUAGES = [
  { code: "auto", label: "Auto-detect", native: "Auto-detect" },
  { code: "hi", label: "Hindi", native: "हिंदी" },
  { code: "mr", label: "Marathi", native: "मराठी" },
  { code: "en", label: "English", native: "English" },
  { code: "ta", label: "Tamil", native: "தமிழ்" },
  { code: "te", label: "Telugu", native: "తెలుగు" },
  { code: "bn", label: "Bengali", native: "বাংলা" },
  { code: "gu", label: "Gujarati", native: "ગુજરાતી" },
  { code: "kn", label: "Kannada", native: "ಕನ್ನಡ" },
  { code: "ml", label: "Malayalam", native: "മലയാളം" },
  { code: "pa", label: "Punjabi", native: "ਪੰਜਾਬੀ" },
] as const;

export function languageName(code: string): string {
  return LANGUAGES.find((l) => l.code === code)?.label ?? code;
}

export const GREETINGS = [
  "नमस्ते",
  "नमस्कार",
  "வணக்கம்",
  "నమస్కారం",
  "নমস্কার",
  "નમસ્તે",
  "ನಮಸ್ಕಾರ",
  "Hello",
];

export const SUGGESTIONS = [
  { icon: "🍅", title: "Crop problem", text: "मेरे टमाटर के पत्ते पीले हो रहे हैं, क्या करूं?", hint: "हिंदी" },
  { icon: "🧅", title: "Mandi price", text: "नाशिक मध्ये कांद्याचा भाव काय आहे?", hint: "मराठी" },
  { icon: "🌧️", title: "Weather", text: "Will it rain in Indore in the next two days?", hint: "English" },
  { icon: "🐛", title: "Pests", text: "kapas me keede lag gaye hai kya kare", hint: "Hinglish" },
];

export const INTENT_LABELS: Record<string, string> = {
  crop_disease: "Crop problem",
  market_price: "Mandi price",
  weather: "Weather",
  general: "General",
  crop_image: "Crop photo",
};
