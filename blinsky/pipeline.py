"""
Pipeline: pipecat-inspired processor chain.
Runs full voice loop: listen -> think -> act -> speak.
Phase 2: wake word loop via WakeWordDetector.
"""
from __future__ import annotations

import threading
from typing import Optional

from blinsky.memory import Memory
from blinsky.processors.ollama_processor import OllamaProcessor, _strip_tool_tags
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
        self._wake_lock = threading.Lock()  # prevent overlapping wake activations

    def _run_tool(self, user_text: str, response: str, tool_call) -> tuple[str, str]:
        if tool_call is None:
            return response, ""
        print(f"[Tools] executing: {tool_call.get('name')} {tool_call.get('args', {})}")
        result = self.tools.execute(tool_call)
        follow_up_prompt = (
            f"Tool '{tool_call.get('name')}' returned:\n{result}\n\n"
            "Using this result, give the user a concise, helpful reply. "
            "Do NOT output any <tool> tags. Just answer naturally."
        )
        final_response, _ = self.ollama.process(follow_up_prompt)
        final_response = _strip_tool_tags(final_response)
        return final_response or result, result

    def run_turn(self, override_text: Optional[str] = None) -> str:
        """Run one full listen→think→act cycle. Returns the final reply text."""
        user_text = override_text or self.whisper.process()
        if not user_text:
            return "[no speech detected]"

        print(f"[User] {user_text}")
        response, tool_call = self.ollama.process(user_text)
        final_response, _ = self._run_tool(user_text, response, tool_call)
        final_response = _strip_tool_tags(final_response)
        print(f"[Blinsky] {final_response}")

        self.ollama.add_turn(user_text, final_response)
        try:
            self.memory.add(self.turn_count, user_text, final_response)
        except Exception:
            pass
        self.turn_count += 1
        return final_response

    # ──────────────────────────────────────────────────────────────────────
    # Phase 2: Wake word loop
    # ──────────────────────────────────────────────────────────────────────

    def _on_wake(self) -> None:
        """Callback fired by WakeWordDetector when wake word is heard."""
        if not self._wake_lock.acquire(blocking=False):
            print("[Pipeline] Already processing a turn — ignoring overlapping wake.")
            return
        try:
            self.tts.speak("Yes?")
            print("[Pipeline] Listening for command...")
            response = self.run_turn()
            if response and response != "[no speech detected]":
                self.tts.speak(response)
            else:
                self.tts.speak("I didn't catch that. Try again.")
        finally:
            self._wake_lock.release()

    def start_wake_word_loop(self) -> None:
        """
        Phase 2 entry point: start Porcupine listener and block until Ctrl+C.
        """
        from blinsky.wake_word import WakeWordDetector

        print("=== Blinsky Phase 2 — Wake Word Mode (Ctrl+C to exit) ===")
        detector = WakeWordDetector(callback=self._on_wake)
        detector.start()

        try:
            detector.wait()
        except KeyboardInterrupt:
            pass
        finally:
            detector.stop()
            print("[Blinsky] Wake word mode stopped.")

    # ──────────────────────────────────────────────────────────────────────
    # Original loops (Phase 1)
    # ──────────────────────────────────────────────────────────────────────

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
