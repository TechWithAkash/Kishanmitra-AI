"""KisanMitra AI — Streamlit chat UI.  Run: uv run streamlit run app.py"""

import hashlib

import streamlit as st

from kisanmitra.entities import locations
from kisanmitra import LANG_NAMES, speech
from kisanmitra.pipeline import describe_language, respond

st.set_page_config(page_title="KisanMitra AI", page_icon="🌾")

LANG_OPTIONS = {"Auto-detect": "auto", "हिंदी (Hindi)": "hi", "मराठी (Marathi)": "mr", "English": "en"}
EXAMPLES = [
    "mera tamatar ka paudha peela ho raha hai, kya karu?",
    "नाशिक मध्ये कांद्याचा भाव काय आहे?",
    "इंदौर में अगले दो दिन बारिश होगी क्या?",
    "What is the price of wheat in Indore?",
]

with st.sidebar:
    st.header("Settings")
    lang_pref = LANG_OPTIONS[st.selectbox("Reply language", list(LANG_OPTIONS))]
    default_loc = st.selectbox("My location (optional)", ["—"] + sorted(locations()))
    default_loc = None if default_loc == "—" else default_loc
    show_details = st.toggle("Show NLP details", value=True)
    if st.button("Clear chat"):
        st.session_state.messages = []
    st.caption("Free data: data.gov.in (Agmarknet), Open-Meteo. Helpline: Kisan Call Centre 1800-180-1551")

st.title("🌾 KisanMitra AI")
st.caption("Ask in your language — type or speak 🎤 — crop problems, mandi prices, weather. / अपनी भाषा में पूछें / तुमच्या भाषेत विचारा")

if "messages" not in st.session_state:
    st.session_state.messages = []


def show_details_panel(reply) -> None:
    with st.expander("NLP details"):
        st.markdown(
            f"**Language:** {describe_language(reply)} &nbsp;|&nbsp; "
            f"**Intent:** `{reply.intent}` ({reply.confidence:.0%})"
        )
        st.markdown("**Entities:** " + ", ".join(f"{k}=`{v}`" for k, v in reply.entities.items() if v) or "none")
        if reply.details.get("nlu_text") and reply.lang not in ("hi", "mr", "en"):
            st.markdown(f"**Translated for understanding:** {reply.details['nlu_text']}")
        heard = reply.details.get("heard")
        if heard:
            st.markdown(
                f"**Voice:** Whisper detected {LANG_NAMES.get(heard['lang'], heard['lang'])} "
                f"({heard['lang_prob']:.0%}); words written by {heard['engine']}"
            )
        st.markdown(f"**English answer (before translation):**\n\n{reply.english}")
        mandi = reply.details.get("mandi")
        if mandi:
            st.markdown(f"**Mandi data source:** {mandi['source']} (match: {mandi['scope']})")
            if mandi["records"]:
                st.dataframe(mandi["records"], hide_index=True)


for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        if msg.get("audio"):
            is_latest = i == len(st.session_state.messages) - 1
            st.audio(msg["audio"], format="audio/mp3", autoplay=is_latest and st.session_state.get("autoplay", False))
        if msg.get("reply") is not None and show_details:
            show_details_panel(msg["reply"])
st.session_state.autoplay = False  # play a voice reply once, not on every rerun

cols = st.columns(len(EXAMPLES))
clicked = next((q for col, q in zip(cols, EXAMPLES) if col.button(q, use_container_width=True)), None)
audio = st.audio_input("🎤 Speak your question in any language / बोलकर पूछें")
query = st.chat_input("Type your question… / अपना सवाल लिखें…") or clicked
voice, heard = False, None

if audio is not None:
    audio_bytes = audio.getvalue()
    digest = hashlib.sha1(audio_bytes).hexdigest()
    if st.session_state.get("last_audio") != digest:  # handle each recording only once
        st.session_state.last_audio = digest
        with st.spinner("Listening… (first time loads the speech model, please wait)"):
            heard = speech.transcribe(audio_bytes)
        if heard.text:
            query, voice = heard.text, True
        else:
            st.warning("I could not hear any words. Please try again closer to the mic.")

if query:
    st.session_state.messages.append({"role": "user", "text": ("🎤 " if voice else "") + query})
    with st.spinner("Thinking…"):
        reply = respond(query, lang_pref=lang_pref, default_location=default_loc, voice=voice,
                        speech_lang=heard.lang if heard else None)
        if heard:
            reply.details["heard"] = heard.__dict__
        audio_reply = speech.speak(reply.spoken, reply.lang) if voice else None
    st.session_state.autoplay = audio_reply is not None
    st.session_state.messages.append({
        "role": "assistant", "text": reply.text.replace("\n", "  \n"), "reply": reply, "audio": audio_reply,
    })
    st.rerun()
