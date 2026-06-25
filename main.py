"""
Main entry: verify Ollama is running, then start voice loop.
Phase 2: --wake flag enables Porcupine wake word mode.
"""
from __future__ import annotations

import os
import socket
import sys

from dotenv import load_dotenv


def check_ollama(host: str = "localhost", port: int = 11434, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    load_dotenv()
    print("[Main] Checking Ollama...")
    if not check_ollama():
        print("[Main] ❌ Ollama not reachable at http://localhost:11434")
        print("       Start it with: ollama serve")
        return 1

    from blinsky.pipeline import BlinskyPipeline
    pipeline = BlinskyPipeline()

    args = set(sys.argv[1:])
    wake_mode  = "--wake"  in args or "-w" in args
    text_mode  = "--text"  in args or "-t" in args

    try:
        if wake_mode:
            print("[Main] 🎙️  Starting Phase 2 — Wake Word Mode")
            pipeline.start_wake_word_loop()
        else:
            pipeline.start_voice_loop(text_mode=text_mode)
    except Exception as exc:
        print(f"[Main] Fatal error: {exc}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
