"""
Local file tools for Blinsky — read/write under ./output/
"""
from __future__ import annotations

import os
from typing import Optional

OUTPUT_DIR = os.path.join(os.getcwd(), "output")


def _ensure_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _resolve(name: str) -> str:
    # prevent path traversal
    base = os.path.basename(name)
    return os.path.join(OUTPUT_DIR, base)


def write_file(filename: str, content: str) -> str:
    _ensure_dir()
    path = _resolve(filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {os.path.basename(filename)} ({len(content)} chars)."


def read_file(filename: str) -> str:
    path = _resolve(filename)
    if not os.path.exists(path):
        return f"File not found: {os.path.basename(filename)}"
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    return f"[{os.path.basename(filename)}]\n{data}"
