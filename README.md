# Blinsky Voice Agent

```text
 ____  _ _           _           
| __ )| (_)_ __  ___| | ___ _   _ 
|  _ \| | | '_ \/ __| |/ / | | | |
| |_) | | | | | \__ \   <| |_| |
|____/|_|_|_| |_|___/_|\_\\__, |
                          |___/ 
```

A fully local, always-on personal AI voice automation agent designed for ultimate privacy and speed. You speak, Blinsky transcribes with faster-whisper, processes with Ollama qwen2.5 (or llama3.2), executes tasks with local tools, and speaks back using pyttsx3. Zero API costs — runs entirely on your PC.

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-qwen2.5-purple.svg)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Status](https://github.com/AneequeShahid/blinsky-voice-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/AneequeShahid/blinsky-voice-agent/actions)

---

## 🏗️ Architecture

```text
       User speaks / types
              ↓
      [WhisperProcessor]  ← mic → faster-whisper (tiny)
              ↓
      [OllamaProcessor]   ← qwen2.5:7b via Ollama ← SkillManager (Phase 4 context injection)
              ↓ (if tool call detected)
      [ToolProcessor]     ← web_search (Tavily) | write_file | read_file
              ↓
      [TTSProcessor]      ← pyttsx3 (speak aloud)
              ↓
      [Memory]            ← ChromaDB + nomic-embed-text (conversation context)
```

---

## ✨ Features

- **Phase 1: Core Voice Pipeline** — Local voice/text processing chain with faster-whisper STT, local LLM reasoning, local file read/write tools, Tavily web search, ChromaDB vector memory, and offline pyttsx3 TTS.
- **Phase 2: Wake Word Detection** — Always-on voice listening via Picovoice Porcupine (configured with the `"blueberry"` keyword by default) so Blinsky wakes up and responds dynamically.
- **Phase 3: Telegram Bot Integration** — Run a dedicated Telegram Bot client linking your local Blinsky instance directly to Telegram, complete with isolated chat histories per user.
- **Phase 4: Skill Learning System** — A persistent, thread-safe skill store. Teach Blinsky arbitrary facts using natural language (e.g. *"remember that my name is Aneeque"*), and the skills are automatically injected into the LLM system prompt.
- **LangGraph Multi-Step Agent** — Multi-step reasoning loops using LangGraph (ReAct agent) to automatically execute sequential tool tasks before returning the final response.

---

## ⚡ Quick Start

Start Blinsky locally in 5 commands:

```bash
# 1. Clone the repository
git clone https://github.com/AneequeShahid/blinsky-voice-agent.git
cd blinsky-voice-agent

# 2. Setup virtual environment & dependencies
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. Pull required local models
ollama pull qwen2.5:7b
ollama pull llama3.2  # Fallback model
ollama pull nomic-embed-text

# 4. Start the backend & open UI
.\start.ps1

# 5. Stop the backend when done
.\stop.ps1
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and configure the following parameters:

| Variable | Description | Requirement |
|----------|-------------|-------------|
| `TAVILY_API_KEY` | Tavily Search Key (free at tavily.com) | Optional (Enables Web Search) |
| `OLLAMA_BASE_URL` | Base URL of local Ollama server | Required (Default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | Main Ollama LLM model | Required (Default: `qwen2.5:7b`) |
| `PICOVOICE_ACCESS_KEY` | Picovoice AccessKey (free at console.picovoice.ai) | Optional (Enables Wake Word) |
| `WAKE_WORD_KEYWORD` | Keyword to trigger wake word detection | Optional (Default: `blueberry`) |
| `WAKE_WORD_SENSITIVITY` | Sensitivity threshold (0.0 to 1.0) | Optional (Default: `0.5`) |
| `TELEGRAM_BOT_TOKEN` | Bot API Token from @BotFather | Optional (Enables Telegram bot) |

---

## 🛠️ REST API Reference

The FastAPI backend runs on port **9001** by default.

### endpoints:
- `GET /health`: Returns `{ "status": "healthy", "uptime_seconds": X }`
- `GET /status`: Returns JSON status of all 4 phases, Ollama connectivity, and tools.
- `POST /chat`: Processes direct conversation using `ChatRequest` model.
- `POST /agent`: Runs LangGraph ReAct agent. Returns steps taken, final response, and tool calls.
- `GET /history`: Retrieves current conversation history array.
- `GET /skills`: Lists all learned skills.
- `POST /skills`: Saves a new skill `{ "name": "...", "content": "..." }`.
- `DELETE /skills/{name}`: Deletes a learned skill.
- `GET /export/json`: Downloads conversation history as JSON file.
- `GET /export/txt`: Downloads conversation history as formatted text.
- `POST /import`: Loads conversation history JSON into session.

---

## 💻 CLI Flags

Run `main.py` directly from the CLI to run local terminal voice loops:

- `python main.py`: Runs default microphone loop (mic → Whisper → LLM → TTS).
- `python main.py --text`: Runs interactive text-only mode inside the terminal.
- `python main.py --wake`: Runs continuous wake word detection mode (requires Picovoice AccessKey).

---

## 🧠 Teaching Blinsky Skills

You can teach Blinsky new skills using the web UI panel, the API endpoints, or simply in conversation:

- *"remember that my office key is under the blue pot"* → Saves a skill named `my office key` containing `under the blue pot`.
- *"what do you know about my office key"* or *"recall my office key"* → Recalls the content.
- *"list skills"* or *"what have you learned"* → Displays all saved notes.
- *"forget my office key"* → Deletes it.

---

## 🗺️ Roadmap & Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Core Local Voice Pipeline & API | Completed ✅ |
| Phase 2 | Always-on Wake Word Detection | Completed ✅ |
| Phase 3 | Telegram Bot Bridge Client | Completed ✅ |
| Phase 4 | Persistent Skill Learning System | Completed ✅ |
| Web UI | Premium Dark UI with Orb animations & agent toggles | Completed ✅ |
| Tests | Pytest test suite & GitHub Actions CI | Completed ✅ |
| Cloud Deploy | Stateless refactor & Railway/Vercel support | In Progress 🚧 |

---

## 🤝 Contributing

Contributions are welcome! Please make sure to install `pytest` and run the tests locally with `python -m pytest tests/ -v` before committing.

## 📄 License

This project is licensed under the [MIT License](LICENSE).
