"""
skills.py — Phase 4 Skill Learning System for Blinsky.

SkillManager provides a persistent, thread-safe key-value store for
named skills (short text notes) that survive across sessions.  Skills
are kept in  data/skills.json  (relative to the project root) and are
automatically injected into the LLM system prompt via inject_context().
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _project_root() -> str:
    """
    Return the absolute path to the project root.

    The module lives at  <root>/blinsky/skills.py, so two dirname() calls
    walk up from this file to the project root.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _skills_path() -> str:
    """Return the absolute path to data/skills.json."""
    return os.path.join(_project_root(), "data", "skills.json")


# ---------------------------------------------------------------------------
# SkillManager
# ---------------------------------------------------------------------------

class SkillManager:
    """
    Persistent skill store for the Blinsky voice agent.

    Skills are stored as a dict keyed by skill name in a JSON file at
    data/skills.json (relative to the project root).  All public methods
    are thread-safe via an internal threading.Lock.

    Skill record schema
    -------------------
    {
        "name":       str,           # unique identifier
        "content":    str,           # the learned text
        "created_at": str            # ISO-8601 UTC timestamp (set on first learn)
    }
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path = _skills_path()

        # Ensure the data/ directory exists before any I/O.
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

        self._skills: dict[str, dict] = self._load()
        print(f"[Skills] Loaded {len(self._skills)} skills from {self._path}")

    # ------------------------------------------------------------------
    # Private I/O (must be called with self._lock held)
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, dict]:
        """
        Read skills from disk.  Returns an empty dict if the file does
        not yet exist or contains invalid JSON.
        """
        if not os.path.isfile(self._path):
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            # raw is expected to be a dict of {name -> skill_record}
            if isinstance(raw, dict):
                return raw
            return {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        """Persist the current in-memory skills dict to disk (lock must be held)."""
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._skills, fh, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def learn(self, name: str, content: str) -> None:
        """
        Add or update a skill by name.

        If the skill already exists its content is updated but the
        original created_at timestamp is preserved.

        Parameters
        ----------
        name:    Unique identifier for the skill (case-preserved).
        content: The text body of the skill.
        """
        name = name.strip()
        content = content.strip()
        with self._lock:
            existing = self._skills.get(name)
            created_at = (
                existing["created_at"]
                if existing
                else datetime.now(timezone.utc).isoformat()
            )
            self._skills[name] = {
                "name": name,
                "content": content,
                "created_at": created_at,
            }
            self._save()
        print(f"[Skills] Learned: '{name}'")

    def forget(self, name: str) -> bool:
        """
        Remove a skill by name.

        Returns
        -------
        True  if the skill existed and was removed.
        False if no skill with that name was found.
        """
        name = name.strip()
        with self._lock:
            if name in self._skills:
                del self._skills[name]
                self._save()
                print(f"[Skills] Forgot: '{name}'")
                return True
        print(f"[Skills] Forget requested for unknown skill: '{name}'")
        return False

    def get(self, name: str) -> Optional[str]:
        """
        Return the content of a skill, or None if it does not exist.

        Parameters
        ----------
        name: The skill name to look up.
        """
        name = name.strip()
        with self._lock:
            record = self._skills.get(name)
        return record["content"] if record else None

    def list_skills(self) -> list[dict]:
        """
        Return all stored skill records sorted alphabetically by name.

        Each record is a dict with keys: name, content, created_at.
        """
        with self._lock:
            skills = list(self._skills.values())
        return sorted(skills, key=lambda s: s["name"].lower())

    def inject_context(self) -> str:
        """
        Build a formatted string of all skills for LLM system prompt injection.

        Returns an empty string when there are no skills.

        Format
        ------
        Learned skills:
          - <name>: <content>
          - <name>: <content>
          ...
        """
        skills = self.list_skills()
        if not skills:
            return ""

        lines = ["Learned skills:"]
        for skill in skills:
            lines.append(f"  - {skill['name']}: {skill['content']}")
        return "\n".join(lines)
