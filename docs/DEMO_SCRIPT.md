# 🎙️ KisanMitra AI — Balanced 50/50 Live Demo Script
**A Perfectly Divided 2-Member Presentation for Evaluators & Teachers**

> **Structure:** Exactly 50% speaking time and demo actions for each member.
> - **Member 1 (Akash):** Intro, Problem, Hinglish Text NLU, Mandi Live Data, Follow-up Memory, and NLP Inspector Sheet.
> - **Member 2 (Partner):** Handover, Hyperlocal Weather & Farming Tips, Hands-Free Voice Mode, AI Leaf Doctor, and Conclusion.

---

## 🟢 PART 1: Presented by Member 1 (Akash)
*(Duration: ~4 Minutes)*

### 1. Introduction & The Problem
**Member 1 (Akash):**
> *"Good morning respected teachers and friends! My name is Akash, and together with my team member, we have built **KisanMitra AI**—an intelligent, multilingual agricultural assistant designed specifically for Indian farmers.*
>
> *Today, millions of Indian farmers have smartphones, but agricultural apps fail them because they are either written in formal English or require navigating complex menus. In reality, a farmer speaks Marathi or Hindi, or types in Latin letters—what we call **Hinglish**.*
>
> *Our goal was to create a conversational assistant that understands text, voice, and leaf photos—running entirely on **free APIs and local on-device AI**."*

---

### 2. Live Demo: Hinglish & Language Intelligence
**[Action: Member 1 opens the chat and types:]**  
`mera tamatar ka paudha peela ho raha hai, kya karu?`

**Member 1 (Akash):**
> *"Let's test our first core feature: **Linguistic Intelligence**.*
>
> *Notice I didn't use Devanagari script. I typed in casual Hinglish: 'mera tamatar ka paudha peela ho raha hai'. Let's hit send.*
>
> *[Bot replies immediately in Romanized Hindi]*
>
> *In under a second, KisanMitra identified the crop as Tomato, diagnosed Yellowing leaves, provided treatment advice, and gave the official Kisan Call Centre helpline (1800-180-1551).*
>
> *Most off-the-shelf NLP detectors fail on Hinglish because they mistake it for Italian or English. Our backend uses **character n-grams (ranges 2 to 5)** with Logistic Regression. So whether a farmer types 'pyaz', 'pyaj', or 'pyaaz', the model captures the subword roots and understands the exact intent!"*

---

### 3. Live Demo: Live Mandi Rates & Conversational Memory
**[Action: Member 1 types:]**  
`Nashik me pyaz ka bhav kya hai?`

**Member 1 (Akash):**
> *"Now let's check market prices. I'm asking: 'What is the onion price in Nashik?'*
>
> *[Bot renders the live Mandi Card]*
>
> *This isn't hardcoded dummy data. KisanMitra connects directly to the Government of India’s Agmarknet API on data.gov.in, giving today's actual modal price per quintal.*
>
> *Now, watch what happens in a real conversation when a farmer asks a follow-up. I won't repeat the question. I will just type three words:"*

**[Action: Member 1 types only 3 words:]**  
`aur Pune me?`

**[Action: Bot gives Onion prices in Pune!]**

**Member 1 (Akash):**
> *"Notice I never said 'onion' or 'price'! Our system has **Dialogue State Tracking**. It remembers that the previous topic was Onion Prices, connects 'Pune' to it, and answers instantly without losing context."*

---

### 4. Behind-the-Scenes: The NLP Inspector Sheet
**[Action: Member 1 clicks the 🧠 Brain icon on the message.]**

**Member 1 (Akash):**
> *"For our teachers and evaluators, we added a transparency feature: clicking this small brain icon opens our **NLP Inspector Sheet**.*
>
> *It reveals exactly what the model decided behind the scenes:*
> - *Detected Language: Hindi (Romanized)*
> - *Predicted Intent: `market_price` with 98% confidence*
> - *Extracted Slots: Crop = Onion, Location = Pune*
> - *Follow-up Memory: Active*
>
> *Now, I will hand over to my partner to show you our weather engine, hands-free voice mode, and on-device AI leaf diagnosis!"*

---

## 🔵 PART 2: Presented by Member 2 (Partner)
*(Duration: ~4 Minutes)*

### 5. Hyperlocal Weather & Agro-Advisory
**Member 2 (Partner):**
> *"Thank you, Akash! Respected teachers, I will now walk you through our real-time weather system, voice interaction, and computer vision model.*
>
> *Farmers don't just want temperature numbers; they need to know what the weather means for their crops. Let's see how KisanMitra handles this."*

**[Action: Member 2 clicks the location pin in the sidebar or 'Use my current location' GPS.]**

**Member 2 (Partner):**
> *"[Action: Weather card loads with 5-day forecast]*
>
> *KisanMitra supports 1-tap browser GPS, which reverse-geocodes your coordinates into the exact village and district.*
>
> *Notice the agronomic tip at the bottom of the card: 'Rain is likely in the next 2 days: postpone pesticide spraying and fertilizer application; ensure fields drain well.'*
>
> *We programmed smart agricultural heuristics into the weather engine: if high winds are predicted, it warns against chemical spray drift; if temperatures drop near freezing, it gives frost protection tips."*

---

### 6. Live Demo: Hands-Free Voice Mode
**[Action: Member 2 clicks the large Microphone 🎙️ button. The glowing animated Voice Orb appears.]**

**Member 2 (Partner):**
> *"Now, what if a farmer cannot read or type? We built a full **Hands-Free Voice Mode**.*
>
> *Watch as I speak to it in Hindi:"*

**[Action: Member 2 speaks clearly into the mic in Hindi:]**  
> *"इंदौर में गेहूं का भाव क्या है?"*  
> *(What is the price of wheat in Indore?)*

**[Action: Visualizer pulses, transcribes the voice, and the bot speaks the answer out loud in natural Hindi voice.]**

**Member 2 (Partner):**
> *"Let's break down what just happened in under 2 seconds:*
> 1. *Our local **faster-whisper AI** detected the spoken language directly from audio waves.*
> 2. *Google’s Speech-to-Text transcribed the words using our custom farming vocabulary hints.*
> 3. *Our pipeline found the wheat price in Indore.*
> 4. *And text-to-speech spoke the answer out loud in natural Hindi! Complete hands-free communication!"*

---

### 7. Live Demo: The AI Crop Leaf Doctor
**[Action: Member 2 clicks ＋ next to the chat box → selects or uploads a photo of a diseased leaf (e.g., Tomato early blight).]**

**Member 2 (Partner):**
> *"Our final and most powerful feature is **The AI Crop Leaf Doctor**.*
>
> *When a farmer spots unusual leaf spots or rotting in the field, they can simply snap a photo with their phone camera or upload it."*

**[Action: Member 2 clicks Send. In under 1 second, the Diagnosis Card appears showing: 'Tomato — Early Blight (94% Confident)' with treatment steps.]**

**Member 2 (Partner):**
> *"Notice how fast that was! Most apps send images to expensive cloud vision APIs. Instead, we fine-tuned a **MobileNetV2 neural network** on the 38-class PlantVillage dataset and converted it to an ONNX runtime.*
>
> *It is only 9 MB in size and runs directly on the CPU in under 40 milliseconds! It evaluates 4 different angles of the leaf, identifies the exact plant pathology, and provides practical organic and chemical remedies."*

---

### 8. Conclusion & Impact
**Member 2 (Partner):**
> *"To conclude our presentation:*
> - *Member 1 (Akash) showed our NLU pipeline handling Hinglish, live government Mandi rates, and multi-turn conversational memory.*
> - *I demonstrated our hyperlocal weather engine, hands-free voice mode, and on-device plant disease diagnosis.*
>
> *KisanMitra AI proves that cutting-edge AI and NLP can be brought to rural India using **100% free APIs and efficient on-device models**.*
>
> *Thank you very much! Akash and I are now ready to answer any questions from the panel."*

---

### 📋 Member Checklist for the Demo:

| Part | Presenter | Key Feature Demonstrated | Technical Highlight Mentioned |
| :---: | :---: | :--- | :--- |
| **Part 1** | **Member 1 (Akash)** | Problem intro, Hinglish query, Tomato yellowing advice | Char n-gram (2–5) TF-IDF + Logistic Regression |
| | | Mandi rates check, follow-up query (*"aur Pune me?"*) | Live Agmarknet data.gov.in API, Dialogue State Tracking |
| | | Brain 🧠 icon inspection sheet | Explainable NLP (confidence score, slots, intent) |
| **Part 2** | **Member 2 (Partner)** | GPS / District weather forecast + farming tips | Dual-provider weather + agronomic heuristics |
| | | Hands-free animated voice mode (speaks in Hindi) | Whisper audio LID + Google STT + gTTS |
| | | Leaf photo upload → Early Blight diagnosis | MobileNetV2 ONNX (~9 MB, 40ms CPU inference) |
| | | Project summary & conclusion | Zero-budget rural AI architecture |
