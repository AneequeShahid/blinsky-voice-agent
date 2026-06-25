# Blinsky Voice Agent

A fully local, always-on personal AI voice automation agent built on top of pipecat-ai/pipecat patterns. You speak, Blinsky transcribes with faster-whisper, thinks with Ollama llama3.2, executes tasks with tools, and speaks back with pyttsx3. Zero API costs — runs entirely on your PC.

```
Mic → Whisper → Ollama(llama3.2) → Tools → pyttsx3 → Speaker
```

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| STT | faster-whisper (tiny) | Local/Free |
| LLM | Ollama llama3.2 | Local/Free |
| TTS | pyttsx3 | Local/Free |
| Agent | LangGraph | Local/Free |
| Search | Tavily (optional free tier) | Free tier |
| Memory | ChromaDB + nomic-embed-text | Local/Free |
| Backend | FastAPI | Local/Free |
| UI | Streamlit | Local/Free |

> **100% local. No API keys required except optional Tavily search.**

## Install

```bash
git clone https://github.com/AneequeShahid/blinsky-voice-agent.git
cd blinsky-voice-agent

python -m venv venv
venv\Scripts\activate   # Windows

pip install -r requirements.txt

ollama pull qwen2.5:7b
ollama pull llama3.2  # fallback model
ollama pull nomic-embed-text
```

## Run

```bash
# Voice loop (needs mic + Ollama running)
python main.py

# API backend
uvicorn api.app:app --reload

# Streamlit UI
streamlit run ui/app.py
```

## Phase Roadmap

- **Phase 1:** Core voice loop (this repo)
- **Phase 2:** Wake word with porcupine
- **Phase 3:** Telegram integration
- **Phase 4:** Skill learning system

---

## Screenshot

_Add screenshot of the Streamlit UI or terminal running the voice loop_
