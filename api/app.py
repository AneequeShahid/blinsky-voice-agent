"""
FastAPI backend for Blinsky — POST /chat returns Ollama response JSON.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from blinsky.memory import Memory
from blinsky.processors.ollama_processor import OllamaProcessor

app = FastAPI(title="Blinsky Voice Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_ollama: OllamaProcessor | None = None
_memory: Memory | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat")
def chat(payload: dict) -> dict:
    user_text = payload.get("message", "")
    if not user_text:
        return {"reply": "Empty message."}
    ov = _get_ollama()
    mv = _get_memory()
    reply, tool_call = ov.process(user_text)
    if tool_call:
        from blinsky.processors.tool_processor import ToolProcessor
        tp = ToolProcessor()
        result = tp.execute(tool_call)
        follow_up = (
            f"Tool result for '{tool_call.get('name')}':\n{result}\n"
            "Now answer the user's original request concisely."
        )
        reply, _ = ov.process(follow_up)
    ov.add_turn(user_text, reply)
    mv.add(mv.collection.count() + 1, user_text, reply)
    return {"reply": reply, "tool_call": tool_call}


def _get_ollama() -> OllamaProcessor:
    global _ollama
    if _ollama is None:
        _ollama = OllamaProcessor()
    return _ollama


def _get_memory() -> Memory:
    global _memory
    if _memory is None:
        _memory = Memory()
    return _memory
