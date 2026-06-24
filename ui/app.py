"""
Streamlit UI for Blinsky — text-input fallback mode.
"""
from __future__ import annotations

import os
import sys

import requests
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from blinsky.memory import Memory  # noqa: E402
from blinsky.pipeline import BlinskyPipeline  # noqa: E402

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
PAGE_TITLE = "Blinsky Voice Agent"

st.set_page_config(page_title=PAGE_TITLE, layout="centered")
st.title(PAGE_TITLE)
st.caption("Local AI voice agent · Ollama llama3.2 · faster-whisper · pyttsx3")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.header("Settings")
    backend = st.text_input("Backend URL", value=BACKEND_URL)
    st.markdown(
        "**Local stack**\n- faster-whisper\n- Ollama llama3.2\n- pyttsx3\n- ChromaDB\n- Streamlit"
    )

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Message Blinsky…"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                r = requests.post(
                    f"{backend}/chat",
                    json={"message": user_input},
                    timeout=120,
                )
                reply = r.json().get("reply", str(r.text))
            except Exception as exc:
                reply = f"Backend error: {exc}"
        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
