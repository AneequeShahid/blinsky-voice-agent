"""
Pipeline: pipecat-inspired processor chain.
Runs full voice loop: listen -> think -> act -> speak.
Phase 2: wake word loop via WakeWordDetector.
Phase 4: skill learning commands intercepted before LLM.
"""
from __future__ import annotations

import re
import threading
from typing import Optional

from blinsky.memory import Memory
from blinsky.processors.ollama_processor import OllamaProcessor, _strip_tool_tags
from blinsky.processors.tool_processor import ToolProcessor
from blinsky.processors.tts_processor import TTSProcessor
from blinsky.processors.whisper_processor import WhisperProcessor
from blinsky.skills import SkillManager


class BlinskyPipeline:
    """Chains Whisper -> Ollama (+ tools) -> TTS in a live voice loop."""

    def __init__(self, keys: Optional[dict] = None, bypass_memory: bool = False) -> None:
        self.whisper = WhisperProcessor()
        
        keys = keys or {}
        ollama_url = keys.get("ollama_url")
        ollama_model = keys.get("ollama_model")
        tavily_key = keys.get("tavily_key")
        
        self.ollama = OllamaProcessor(base_url=ollama_url, model_name=ollama_model)
        self.tools = ToolProcessor(tavily_key=tavily_key)
        self.tts = TTSProcessor()
        
        self.bypass_memory = bypass_memory
        if not bypass_memory:
            try:
                from blinsky.memory import Memory
                self.memory = Memory()
            except Exception:
                self.memory = None
        else:
            self.memory = None
            
        self.skills = SkillManager()  # Phase 4: skill learning
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

    def run_turn(self, override_text: Optional[str] = None, use_agent: bool = False) -> str:
        """Run one full listen→think→act cycle. Returns the final reply text."""
        user_text = override_text or self.whisper.process()
        if not user_text:
            return "[no speech detected]"

        print(f"[User] {user_text}")

        # ── Phase 4: Skill command detection ─────────────────────────────
        skill_response = self._handle_skill_command(user_text)
        if skill_response is not None:
            print(f"[Blinsky] {skill_response}")
            self.tts.speak(skill_response)
            return skill_response
        # ─────────────────────────────────────────────────────────────────

        if use_agent:
            from blinsky.agent import run_agent
            res = run_agent(user_text, self.ollama.history)
            final_response = res["reply"]
            for step in res["steps"]:
                print(f"[Agent Step] {step}")
        else:
            response, tool_call = self.ollama.process(user_text)
            final_response, _ = self._run_tool(user_text, response, tool_call)
            final_response = _strip_tool_tags(final_response)

        print(f"[Blinsky] {final_response}")

        self.ollama.add_turn(user_text, final_response)
        if self.memory:
            try:
                self.memory.add(self.turn_count, user_text, final_response)
            except Exception:
                pass
        self.turn_count += 1
        return final_response

    # ──────────────────────────────────────────────────────────────────────
    # Phase 4: Skill command handler
    # ──────────────────────────────────────────────────────────────────────

    _RE_REMEMBER_IS = re.compile(
        r'^remember\s+that\s+(.+?)\s+is\s+(.+)$', re.IGNORECASE
    )
    _RE_REMEMBER_COLON = re.compile(
        r'^remember\s+that\s+(.+?):\s*(.+)$', re.IGNORECASE
    )
    _RE_FORGET = re.compile(
        r'^forget\s+(.+)$', re.IGNORECASE
    )
    _RE_WHAT_KNOW = re.compile(
        r'^what\s+do\s+you\s+know\s+about\s+(.+)$', re.IGNORECASE
    )
    _RE_RECALL = re.compile(
        r'^recall\s+(.+)$', re.IGNORECASE
    )
    _RE_LIST = re.compile(
        r'^(?:list\s+skills|what\s+have\s+you\s+learned)$', re.IGNORECASE
    )

    def _handle_skill_command(self, user_text: str) -> Optional[str]:
        """
        Attempt to match user_text against known skill commands.

        Returns a reply string if the text was a skill command, or None
        if it should be forwarded to the LLM as normal.
        """
        text = user_text.strip()

        # --- remember that <name> is <content> ---
        m = self._RE_REMEMBER_IS.match(text)
        if not m:
            m = self._RE_REMEMBER_COLON.match(text)
        if m:
            name, content = m.group(1).strip(), m.group(2).strip()
            self.skills.learn(name, content)
            return f"Got it! I will remember that {name} is {content}."

        # --- forget <name> ---
        m = self._RE_FORGET.match(text)
        if m:
            name = m.group(1).strip()
            existed = self.skills.forget(name)
            if existed:
                return f"Done! I have forgotten everything I knew about {name}."
            return f"I don't have any notes on {name}, so there's nothing to forget."

        # --- what do you know about <name> / recall <name> ---
        m = self._RE_WHAT_KNOW.match(text)
        if not m:
            m = self._RE_RECALL.match(text)
        if m:
            name = m.group(1).strip()
            content = self.skills.get(name)
            if content:
                return f"Here is what I know about {name}: {content}"
            return f"I don't have any notes on {name}."

        # --- list skills / what have you learned ---
        if self._RE_LIST.match(text):
            skills = self.skills.list_skills()
            if not skills:
                return "I haven't learned any skills yet."
            bullet_lines = [f"  • {s['name']}: {s['content']}" for s in skills]
            return "Here is what I have learned:\n" + "\n".join(bullet_lines)

        # No skill command matched — forward to LLM.
        return None

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
