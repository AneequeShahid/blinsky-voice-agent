"""
WakeWordDetector: wraps pvporcupine + sounddevice to listen for a wake word
on the microphone and fire a callback when detected.
"""
from __future__ import annotations

import os
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_KEYWORDS = [
    "blueberry", "bumblebee", "alexa", "hey siri", "hey google",
    "ok google", "computer", "jarvis", "picovoice", "porcupine",
    "terminator", "grasshopper", "americano", "grapefruit",
]


class WakeWordDetector:
    """
    Continuously listens on the microphone for a configured wake word.
    When detected, calls the provided callback on a background thread.

    Requires PICOVOICE_ACCESS_KEY in .env.

    Usage:
        def on_wake():
            print("Wake word heard!")

        detector = WakeWordDetector(callback=on_wake)
        detector.start()          # non-blocking, runs in background
        detector.wait()           # block until stopped (e.g. main thread)
        detector.stop()
    """

    def __init__(
        self,
        callback: Callable[[], None],
        keyword: Optional[str] = None,
        sensitivity: Optional[float] = None,
    ) -> None:
        self.callback = callback
        self.keyword = (keyword or os.getenv("WAKE_WORD_KEYWORD", "blueberry")).lower()
        self.sensitivity = float(sensitivity or os.getenv("WAKE_WORD_SENSITIVITY", "0.5"))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._porcupine = None

    def _validate_keyword(self) -> str:
        """Ensure keyword is valid for the free tier."""
        if self.keyword not in SUPPORTED_KEYWORDS:
            print(
                f"[WakeWord] WARNING: '{self.keyword}' is not in the supported list.\n"
                f"           Supported: {SUPPORTED_KEYWORDS}\n"
                f"           Falling back to 'blueberry'."
            )
            return "blueberry"
        return self.keyword

    def _load_porcupine(self):
        """Lazy-load Porcupine; raises clearly if AccessKey is missing."""
        try:
            import pvporcupine
        except ImportError:
            raise RuntimeError(
                "[WakeWord] pvporcupine is not installed.\n"
                "           Run: pip install pvporcupine"
            )

        access_key = os.getenv("PICOVOICE_ACCESS_KEY", "").strip()
        if not access_key:
            raise RuntimeError(
                "[WakeWord] PICOVOICE_ACCESS_KEY is not set.\n"
                "           1. Sign up free at https://console.picovoice.ai/\n"
                "           2. Copy your AccessKey\n"
                "           3. Add it to .env: PICOVOICE_ACCESS_KEY=your_key_here\n"
                "           Then restart Blinsky."
            )

        keyword = self._validate_keyword()
        print(f"[WakeWord] Loading Porcupine — keyword='{keyword}' sensitivity={self.sensitivity}")

        porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=[keyword],
            sensitivities=[self.sensitivity],
        )
        return porcupine

    def _listen_loop(self) -> None:
        """Main blocking listen loop — runs on a background thread."""
        try:
            self._porcupine = self._load_porcupine()
        except RuntimeError as exc:
            print(str(exc))
            return

        frame_length = self._porcupine.frame_length
        sample_rate = self._porcupine.sample_rate

        print(
            f"[WakeWord] ✅ Listening for '{self.keyword}' "
            f"(frame={frame_length}, sr={sample_rate}) — say it to activate Blinsky!"
        )

        def audio_callback(indata, frames, time, status):
            if self._stop_event.is_set():
                raise sd.CallbackStop()
            pcm = (indata[:, 0] * 32767).astype(np.int16)
            result = self._porcupine.process(pcm)
            if result >= 0:
                print(f"\n[WakeWord] 🎙️  Wake word '{self.keyword}' detected!")
                threading.Thread(target=self.callback, daemon=True).start()

        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=frame_length,
            callback=audio_callback,
        ):
            self._stop_event.wait()  # block until stop() is called

        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None

        print("[WakeWord] Stopped.")

    def start(self) -> None:
        """Start the wake word detector in a daemon thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="WakeWordThread")
        self._thread.start()

    def stop(self) -> None:
        """Signal the detector to stop."""
        self._stop_event.set()

    def wait(self) -> None:
        """Block the calling thread until stop() is called (use in main thread)."""
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=1.0)
        except KeyboardInterrupt:
            self.stop()
