"""
Main entry: verify Ollama is running, then start voice loop.
"""
from __future__ import annotations

import os
import socket
import sys

from blinsky.pipeline import BlinskyPipeline
from dotenv import load_dotenv


def check_ollama(host: str = "localhost", port: int = 11434, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    load_dotenv()
    print("[Main] checking ollama...")
    if not check_ollama():
        print("[Main] Ollama not reachable at http://localhost:11434")
        print("       Start Ollama or run:ollama serve")
        return 1
    pipeline = BlinskyPipeline()
    text_mode = len(sys.argv) > 1 and sys.argv[1] in {"--text", "text", "-t"}
    try:
        pipeline.start_voice_loop(text_mode=text_mode)
    except Exception as exc:
        print(f"[Main] fatal: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
