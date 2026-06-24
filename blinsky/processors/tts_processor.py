"""
TTSProcessor: convert text response to speech with pyttsx3, play audio.
"""
from __future__ import annotations

import threading
from typing import Optional

import pyttsx3


class TTSProcessor:
    """Text-to-speech via pyttsx3. Safe to call from any thread."""

    def __init__(self, rate: int = 170, volume: float = 1.0) -> None:
        self.rate = rate
        self.volume = volume
        self._engine: Optional[pyttsx3.Engine] = None

    def _get_engine(self) -> pyttsx3.Engine:
        if self._engine is None:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            voices = engine.getProperty("voices")
            if voices:
                for v in voices:
                    name = (v.name or "").lower()
                    if "zira" in name or "david" in name or "english" in name:
                        engine.setProperty("voice", v.id)
                        break
            self._engine = engine
        return self._engine

    def speak(self, text: str) -> None:
        """Speak text aloud (blocking)."""
        if not text:
            return
        engine = self._get_engine()
        try:
            engine.say(text)
            engine.runAndWait()
        except RuntimeError:
            # pyttsx3 run loop already running — reinit
            self._engine = None
            self.speak(text)

    def speak_async(self, text: str) -> None:
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()
