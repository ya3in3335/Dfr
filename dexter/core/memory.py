"""Lightweight conversation memory.

Keeps a rolling window of the dialogue in memory and optionally persists a
compact history to disk so Dexter remembers across restarts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class Memory:
    def __init__(self, path: Path, max_turns: int = 40):
        self.path = path
        self.max_turns = max_turns
        self.messages: List[Dict[str, str]] = self._load()

    def _load(self) -> List[Dict[str, str]]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data[-self.max_turns:]
            except Exception:
                pass
        return []

    def _save(self) -> None:
        try:
            self.path.write_text(
                json.dumps(self.messages[-self.max_turns:], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_turns:
            self.messages = self.messages[-self.max_turns:]
        self._save()

    def recent(self, limit: int = 20) -> List[Dict[str, str]]:
        return self.messages[-limit:]

    def clear(self) -> None:
        self.messages = []
        self._save()
