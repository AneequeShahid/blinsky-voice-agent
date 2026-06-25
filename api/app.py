"""
FastAPI backend for Blinsky — POST /chat returns Ollama response JSON.
"""
from __future__ import annotations

import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from blinsky.memory import Memory
from blinsky.processors.ollama_processor import OllamaProcessor, _strip_tool_tags

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
    return {"status": "healthy"}


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(payload: ChatRequest) -> dict:
    user_text = payload.message.strip()
    if not user_text:
        return {"reply": "Please say something!"}

    ov = _get_ollama()
    mv = _get_memory()

    reply, tool_call = ov.process(user_text)

    if tool_call:
        from blinsky.processors.tool_processor import ToolProcessor
        tp = ToolProcessor()
        result = tp.execute(tool_call)

        follow_up = (
            f"Tool '{tool_call.get('name')}' returned:\n{result}\n\n"
            "Using this result, give the user a concise, helpful reply. "
            "Do NOT output any <tool> tags. Just answer naturally."
        )
        reply, _ = ov.process(follow_up)

    # Final safety net: strip any <tool> garbage that leaked through
    reply = _strip_tool_tags(reply)

    if not reply:
        reply = "I ran into an issue generating a response. Please try again."

    ov.add_turn(user_text, reply)
    try:
        mv.add(mv.collection.count() + 1, user_text, reply)
    except Exception:
        pass  # Memory errors are non-fatal

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
