"""
run_telegram.py — Standalone entry-point for the Blinsky Telegram bot.

Usage:
    python -m blinsky.run_telegram
    # or
    python blinsky/run_telegram.py

Pre-flight checks performed before starting:
  1. .env loaded (TELEGRAM_BOT_TOKEN must be set there or in the environment).
  2. Ollama reachable at localhost:11434 — bot won't start if Ollama is down.
"""
from __future__ import annotations

import asyncio
import socket
import sys

from dotenv import load_dotenv

# Load environment variables from .env BEFORE importing any Blinsky module
# so that TELEGRAM_BOT_TOKEN and OLLAMA_BASE_URL are available immediately.
load_dotenv()

from blinsky.telegram_bot import TelegramBridge  # noqa: E402 — must come after load_dotenv


# ---------------------------------------------------------------------------
# Helper: Ollama reachability check
# ---------------------------------------------------------------------------

def _ollama_reachable(host: str = "localhost", port: int = 11434) -> bool:
    """
    Return True if a TCP connection to *host*:*port* succeeds within 2 s.

    Uses a raw socket so we don't need the ``requests`` library at this stage.
    """
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (OSError, ConnectionRefusedError):
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run all pre-flight checks, then start the Telegram bot."""

    # --- Check 1: Ollama must be running -----------------------------------
    print("[Blinsky] Checking Ollama availability at localhost:11434 …")
    if not _ollama_reachable():
        print(
            "[Blinsky] ERROR: Cannot reach Ollama at localhost:11434.\n"
            "          Please start Ollama first:  ollama serve\n"
            "          Then re-run this script."
        )
        sys.exit(1)

    print("[Blinsky] Ollama is reachable. Starting Telegram bot …")

    # --- Start the bot -----------------------------------------------------
    bridge = TelegramBridge()
    asyncio.run(bridge.run())


if __name__ == "__main__":
    main()
