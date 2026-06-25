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

# Matches any <tool ...> tag — opening, closing, self-closing, broken
_TOOL_GARBAGE_RE = re.compile(r"</?tool[^>]*>", re.DOTALL)


def _strip_tool_tags(text: str) -> str:
    """Remove every <tool>, </tool>, <tool .../> tag from text."""
    return _TOOL_GARBAGE_RE.sub("", text).strip()


def _extract_json(text: str) -> Optional[dict]:
    """
    Try to extract the first valid JSON object from text.
    Handles nested braces so partial/broken JSON fails gracefully.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
    return None


class OllamaProcessor:
    """Sends user transcript to local Ollama and returns text + optional tool call."""

    SYSTEM_PROMPT = (
        "You are Blinsky, a helpful and concise local AI assistant. "
        "You have access to these tools:\n"
        "  web_search(query) — search the web\n"
        "  write_file(filename, content) — write a local file\n"
        "  read_file(filename) — read a local file\n\n"
        "TOOL CALL FORMAT — use this EXACT format when you need a tool:\n"
        '  <tool>{"name": "web_search", "args": {"query": "your query here"}}</tool>\n\n'
        "RULES:\n"
        "  1. Put the JSON BETWEEN <tool> and </tool>. Always close the tag.\n"
        "  2. The JSON must have 'name' and 'args' keys.\n"
        "  3. Never put anything else inside the <tool> block.\n"
        "  4. Only call ONE tool per response.\n"
        "  5. If you don't need a tool, reply naturally in 1-2 sentences.\n"
        "  6. Never output a <tool> tag unless you intend to call a tool.\n"
    )

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self.llm = OllamaLLM(
            model=MODEL_NAME,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
        )
        self.system_prompt = system_prompt or self.SYSTEM_PROMPT
        self.history: list[dict[str, str]] = []

    def _build_prompt(self, user_text: str) -> str:
        lines: list[str] = [f"System: {self.system_prompt}"]
        for turn in self.history[-10:]:
            lines.append(f"User: {turn['user']}")
            lines.append(f"Assistant: {turn['assistant']}")
        lines.append(f"User: {user_text}")
        lines.append("Assistant:")
        return "\n".join(lines)

    def _parse_tool_call(self, text: str) -> Optional[dict]:
        """
        Robustly detect any tool call in model output.
        Handles: <tool>{...}</tool>, unclosed <tool>{...}, broken <tool>}
        """
        if "<tool" not in text:
            return None

        # Extract JSON from anywhere after <tool>
        tool_start = text.find("<tool")
        after_tag = text[tool_start:]

        # Find the first { after the opening tag
        brace_pos = after_tag.find("{")
        if brace_pos == -1:
            # No JSON object at all (e.g. <tool>} or <tool/>)
            return None

        return _extract_json(after_tag[brace_pos:])

    def process(self, user_text: str) -> Tuple[str, Optional[dict]]:
        """Return (final_text, tool_call_or_None)."""
        prompt = self._build_prompt(user_text)
        try:
            raw = self.llm.invoke(prompt)
        except Exception as exc:
            print(f"[Ollama] error: {exc}")
            return "Sorry, I'm having trouble connecting to Ollama right now.", None

        print(f"[Ollama] raw output: {repr(raw)}")  # debug log

        tool_call = self._parse_tool_call(raw)

        if tool_call:
            # Strip all <tool> tags from text before returning
            clean = _strip_tool_tags(raw)
            return clean, tool_call

        # No tool call — still strip any accidental tag garbage
        clean = _strip_tool_tags(raw)

        # If stripping wiped everything, return a safe fallback
        if not clean:
            return "I couldn't generate a response. Please try again.", None

        return clean, None

    def add_turn(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"user": user_text, "assistant": assistant_text})
