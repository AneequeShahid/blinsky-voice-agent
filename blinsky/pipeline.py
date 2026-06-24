"""
Pipeline: pipecat-inspired processor chain.
Runs full voice loop: listen -> think -> act -> speak.
"""
from __future__ import annotations

from typing import Optional

from blinsky.memory import Memory
from blinsky.processors.ollama_processor import OllamaProcessor
from blinsky.processors.tool_processor import ToolProcessor
from blinsky.processors.tts_processor import TTSProcessor
from blinsky.processors.whisper_processor import WhisperProcessor


class BlinskyPipeline:
    """Chains Whisper -> Ollama (+ tools) -> TTS in a live voice loop."""

    def __init__(self) -> None:
        self.whisper = WhisperProcessor()
        self.ollama = OllamaProcessor()
        self.tools = ToolProcessor()
        self.tts = TTSProcessor()
        self.memory = Memory()
        self.turn_count = 0

    def _maybe_ingest_tool(self, user_text: str, response: str, tool_call) -> tuple[str, str]:
        if tool_call is None:
            return response, ""
        print(f"[Tools] executing: {tool_call.get('name')} {tool_call.get('args', {})}")
        result = self.tools.execute(tool_call)
        follow_up_prompt = (
            f"Tool result for '{tool_call.get('name')}':\n{result}\n"
            "Now answer the user's original request concisely."
        )
        final_response, _ = self.ollama.process(follow_up_prompt)
        return final_response, result

    def run_turn(self, override_text: Optional[str] = None) -> str:
        user_text = override_text or self.whisper.process()
        if not user_text:
            return "[no speech detected]"

        print(f"[User] {user_text}")
        response, tool_call = self.ollama.process(user_text)
        final_response, _ = self._maybe_ingest_tool(user_text, response, tool_call)
        print(f"[Blinsky] {final_response}")

        self.ollama.add_turn(user_text, final_response)
        self.memory.add(self.turn_count, user_text, final_response)
        self.turn_count += 1
        return final_response

    def start_voice_loop(self, text_mode: bool = False) -> None:
        print("=== Blinsky Voice Agent (Ctrl+C to exit) ===")
        try:
            while True:
                if text_mode:
                    user_text = input("[You] ")
                    if user_text.lower() in {"exit", "quit", "bye"}:
                        print("[Blinsky] Goodbye.")
                        break
                    response = self.run_turn(override_text=user_text)
                    print("[Speaking...]")
                    self.tts.speak(response)
                else:
                    print("Listening...")
                    response = self.run_turn()
                    print("Speaking...")
                    self.tts.speak(response)
        except KeyboardInterrupt:
            print("\n[Blinsky] Shutting down.")
