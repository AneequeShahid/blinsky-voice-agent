"""
OllamaProcessor: send transcript + history to Ollama llama3.2,
detect tool use, return response and tool call if any.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional, Tuple

from dotenv import load_dotenv
from langchain_ollama import OllamaLLM

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = "llama3.2"
TOOL_TAG_RE = re.compile(r"<tool>(.*?)</tool>", re.DOTALL)


class OllamaProcessor:
    """Sends user transcript to local Ollama and returns text + optional tool call."""

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self.llm = OllamaLLM(
            model=MODEL_NAME,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3,
        )
        self.system_prompt = system_prompt or (
            "You are Blinsky, a concise local voice assistant. "
            "If you need to call a tool, output it ONLY inside a single <tool>... </tool> "
            "XML block as JSON with keys: name and args. "
            "For web search use: {\"name\": \"web_search\", \"args\": {\"query\": \"...\"}}. "
            "For file write use: {\"name\": \"write_file\", \"args\": {\"filename\": \"...\", \"content\": \"...\"}}. "
            "For file read use: {\"name\": \"read_file\", \"args\": {\"filename\": \"...\"}}. "
            "Otherwise reply naturally in one or two sentences. "
            "Output a final user-facing reply after tool results when applicable."
        )
        self.history: list[dict[str, str]] = []

    def _build_prompt(self, user_text: str) -> str:
        lines: list[str] = [f"System: {self.system_prompt}"]
        for turn in self.history[-10:]:
            lines.append(f"User: {turn['user']}")
            lines.append(f"Assistant: {turn['assistant']}")
        lines.append(f"User: {user_text}")
        return "\n".join(lines)

    def _parse_tool_call(self, text: str) -> Optional[dict]:
        m = TOOL_TAG_RE.search(text)
        if not m:
            return None
        raw = m.group(1).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def process(self, user_text: str) -> Tuple[str, Optional[dict]]:
        """Return (final_text, tool_call_or_None)."""
        prompt = self._build_prompt(user_text)
        try:
            raw = self.llm.invoke(prompt)
        except Exception as exc:
            print(f"[Ollama] error: {exc}")
            raw = "Sorry, I'm having trouble thinking right now."

        tool_call = self._parse_tool_call(raw)
        if tool_call:
            # strip <tool> block so history stores clean text
            clean = TOOL_TAG_RE.sub("", raw).strip()
            return clean or raw, tool_call

        return raw, None

    def add_turn(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"user": user_text, "assistant": assistant_text})
