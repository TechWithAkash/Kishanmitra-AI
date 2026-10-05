# 🌾 KisanMitra AI

A multilingual NLP chatbot for Indian farmers. Ask about **crop problems, mandi prices or weather** in **Hindi, Marathi, English or romanized Hindi**, and get the answer back in the same language.

Uses **only free APIs**: data.gov.in (Agmarknet), Open-Meteo, and the free Google Translate endpoint.

- `mvp.md` — what the NLP core implements (start here)
- `frontend-plan.md` — the Next.js chat + voice UI
- `plan.md` — the full long-term vision

## Run (ChatGPT-style web app: chat + voice mode)

Two terminals:

```bash
# 1. backend (Python / FastAPI)
uv sync
uv run uvicorn kisanmitra.server:app --port 8000

# 2. frontend (Next.js + shadcn/ui + Magic UI)
cd web && npm install && npm run dev      # open http://localhost:3000
```

If port 3000 is busy, use `npm run dev -- -p 3200`. Use Chrome or Edge for the microphone.

Quick debug UI (Streamlit, no Node needed): `uv run streamlit run app.py`

```bash
uv run pytest                    # backend tests (offline)
cd web && npm run lint && npm run build
uv run python -m kisanmitra.intent   # intent model accuracy report
```

Without `uv`: `pip install -r requirements.txt && streamlit run app.py`.

Optional: get a free API key from [data.gov.in](https://data.gov.in) and set `DATA_GOV_API_KEY` for more mandi results. Without it, the public sample key is used. If the mandi API is down, the app shows clearly-labelled sample prices.

## Pipeline

1. **Language detection** (`kisanmitra/langid.py`): Unicode script, plus marker words for Hindi vs Marathi and romanized Hindi
2. **Intent** (`kisanmitra/intent.py`): TF-IDF char n-grams + Logistic Regression, 4 intents
3. **Entities** (`kisanmitra/entities.py`): multilingual keyword lists for crop, symptom and location
4. **Answer**: advice knowledge base, live mandi prices, or Open-Meteo weather with farming tips
5. **Translate back** (`kisanmitra/translate.py`), romanized if the user typed in Latin script

## Crop photo check

Tap **＋** in the text box → **Take a photo** (live camera) or **Upload a photo** (you can also paste or drag-and-drop an image). Pick the crop if you know it, add an optional note, and send.

- Model: MobileNetV2 trained on PlantVillage, ONNX, runs locally with `onnxruntime` (no API key, ~9 MB, downloaded on first start).
- Works for tomato, potato, maize, pepper, grape, apple, peach, cherry, strawberry, squash and orange. Not onion, wheat, cotton, rice or chilli: the app says so instead of guessing.
- **Limits:** the model learned from single leaves on plain backgrounds, so field photos with many leaves are less reliable, and some diseases look alike (e.g. early vs late blight). Results are labelled Confident / Possible / Not sure, and always point to the Kisan Call Centre.
- Test images: [PlantVillage dataset](https://github.com/spMohanty/PlantVillage-Dataset/tree/master/raw/color).

## Voice

- **Voice mode:** the mic button opens an animated voice window: hands-free conversation (speak → answer is read aloud → listens again). Tap the orb to send early or skip the answer.
- Speech-to-text: Whisper detects the language, Google's free recognizer writes the words (Whisper is the offline fallback). Text-to-speech: gTTS. All free.
