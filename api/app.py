"""
FastAPI backend for Blinsky — All 4 phases integrated.
Endpoints: /chat  /skills  /status  /history  /health
"""
from __future__ import annotations

import os
import socket
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from blinsky.processors.ollama_processor import OllamaProcessor, _strip_tool_tags
from blinsky.processors.tool_processor import ToolProcessor
from blinsky.pipeline import BlinskyPipeline
from blinsky.skills import SkillManager

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Blinsky API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singletons ────────────────────────────────────────────────────────────────

_pipeline: Optional[BlinskyPipeline] = None
_start_time = time.time()


def _get_pipeline() -> BlinskyPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = BlinskyPipeline()
    return _pipeline


def _ollama_alive() -> bool:
    try:
        host = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        host = host.replace("http://", "").replace("https://", "").split(":")[0]
        port = int(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").split(":")[-1]) if ":" in os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").split("//")[-1] else 11434
        socket.create_connection((host, port), timeout=1.0).close()
        return True
    except OSError:
        return False


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class SkillLearnRequest(BaseModel):
    name: str
    content: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "uptime_seconds": round(time.time() - _start_time)}


@app.get("/status")
def status() -> dict:
    """Returns status of all 4 phases."""
    telegram_token = bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip())
    picovoice_key  = bool(os.getenv("PICOVOICE_ACCESS_KEY", "").strip())
    tavily_key     = bool(os.getenv("TAVILY_API_KEY", "").strip())
    skills         = _get_pipeline().skills.list_skills()

    return {
        "ollama":    _ollama_alive(),
        "phase1":    {"name": "Voice Pipeline", "active": _ollama_alive()},
        "phase2":    {"name": "Wake Word",       "active": picovoice_key,  "keyword": os.getenv("WAKE_WORD_KEYWORD", "blueberry")},
        "phase3":    {"name": "Telegram Bot",    "active": telegram_token},
        "phase4":    {"name": "Skill Learning",  "active": True, "skill_count": len(skills)},
        "tools":     {"web_search": tavily_key, "file_ops": True},
        "uptime":    round(time.time() - _start_time),
    }


@app.post("/chat")
def chat(payload: ChatRequest) -> dict:
    user_text = payload.message.strip()
    if not user_text:
        return {"reply": "Please say something!", "tool_call": None, "skill_action": None}

    pipeline = _get_pipeline()

    # Phase 4: check skill commands first
    skill_response = pipeline._handle_skill_command(user_text)
    if skill_response is not None:
        return {"reply": skill_response, "tool_call": None, "skill_action": True}

    # Phase 1: LLM + tools
    reply, tool_call = pipeline.ollama.process(user_text)

    if tool_call:
        result = pipeline.tools.execute(tool_call)
        follow_up = (
            f"Tool '{tool_call.get('name')}' returned:\n{result}\n\n"
            "Using this result, give the user a concise, helpful reply. "
            "Do NOT output any <tool> tags. Just answer naturally."
        )
        reply, _ = pipeline.ollama.process(follow_up)

    reply = _strip_tool_tags(reply)
    if not reply:
        reply = "I ran into an issue generating a response. Please try again."

    pipeline.ollama.add_turn(user_text, reply)
    try:
        pipeline.memory.add(pipeline.turn_count, user_text, reply)
        pipeline.turn_count += 1
    except Exception:
        pass

    return {"reply": reply, "tool_call": tool_call, "skill_action": False}


@app.post("/agent")
def agent_chat(payload: ChatRequest) -> dict:
    user_text = payload.message.strip()
    if not user_text:
        return {"reply": "Please say something!", "steps": [], "tool_calls": [], "skill_action": None}

    pipeline = _get_pipeline()

    # Phase 4: check skill commands first
    skill_response = pipeline._handle_skill_command(user_text)
    if skill_response is not None:
        return {
            "reply": skill_response,
            "steps": [f"Skill command detected: {user_text}"],
            "tool_calls": [],
            "skill_action": True
        }

    from blinsky.agent import run_agent
    res = run_agent(user_text, pipeline.ollama.history)

    pipeline.ollama.add_turn(user_text, res["reply"])
    try:
        pipeline.memory.add(pipeline.turn_count, user_text, res["reply"])
        pipeline.turn_count += 1
    except Exception:
        pass

    return {
        "reply": res["reply"],
        "steps": res["steps"],
        "tool_calls": res["tool_calls"],
        "skill_action": False
    }


@app.get("/history")
def history() -> dict:
    """Return conversation history for the current session."""
    return {"history": _get_pipeline().ollama.history}


@app.get("/skills")
def list_skills() -> dict:
    return {"skills": _get_pipeline().skills.list_skills()}


@app.post("/skills")
def learn_skill(payload: SkillLearnRequest) -> dict:
    if not payload.name.strip() or not payload.content.strip():
        raise HTTPException(status_code=400, detail="name and content are required")
    _get_pipeline().skills.learn(payload.name.strip(), payload.content.strip())
    return {"ok": True, "message": f"Learned: {payload.name}"}


@app.delete("/skills/{name}")
def forget_skill(name: str) -> dict:
    existed = _get_pipeline().skills.forget(name)
    if not existed:
        raise HTTPException(status_code=404, detail=f"No skill named '{name}'")
    return {"ok": True, "message": f"Forgot: {name}"}


from fastapi.responses import JSONResponse, PlainTextResponse
import json as json_lib

@app.get("/export/json")
def export_json() -> JSONResponse:
    """Download conversation history as JSON."""
    history = _get_pipeline().ollama.history
    content = json_lib.dumps({"history": history, "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=2)
    return JSONResponse(
        content=json_lib.loads(content),
        headers={"Content-Disposition": "attachment; filename=blinsky_conversation.json"}
    )

@app.get("/export/txt", response_class=PlainTextResponse)
def export_txt() -> str:
    """Download conversation history as readable text file."""
    history = _get_pipeline().ollama.history
    lines = ["Blinsky Conversation Export", "=" * 40, ""]
    for turn in history:
        lines.append(f"Aneeque: {turn.get('user', '')}")
        lines.append(f"Blinsky: {turn.get('assistant', '')}")
        lines.append("")
    content = "\n".join(lines)
    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": "attachment; filename=blinsky_conversation.txt"}
    )

class ImportRequest(BaseModel):
    history: list

@app.post("/import")
def import_history(payload: ImportRequest) -> dict:
    """Load conversation history into the current session."""
    pipeline = _get_pipeline()
    pipeline.ollama.history = payload.history
    return {"ok": True, "loaded": len(payload.history), "message": f"Loaded {len(payload.history)} turns"}
