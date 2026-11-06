"""Consent & permission system for Dexter Cyber.

Design goals
------------
* **Explicit first-run consent.** On first launch the user sees exactly which
  capabilities they are granting. Nothing sensitive runs until they approve.
* **One-time by default.** The decision is persisted locally (in the user's
  home, never in the repo) so the user is only asked once — matching the
  "approve on first login only" requirement.
* **Granular & revocable.** Each capability is an independent grant and can be
  turned off again at any time from the UI.
* **Local only.** Consent lives on the user's machine; it is never uploaded.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class Capability:
    key: str
    title: str
    description: str
    risk: str  # "low" | "medium" | "high"


# The full set of privileges Dexter can be granted. The UI renders these on the
# first-run consent screen so the user knows exactly what they are approving.
CAPABILITIES: List[Capability] = [
    Capability(
        key="screen_vision",
        title="See the screen",
        description="Capture screenshots of your display so Dexter can understand what is on screen.",
        risk="medium",
    ),
    Capability(
        key="mouse_keyboard",
        title="Control mouse & keyboard",
        description="Move the cursor, click, and type on your behalf to operate applications.",
        risk="high",
    ),
    Capability(
        key="run_commands",
        title="Run system commands",
        description="Execute shell commands on this computer (e.g. open apps, manage files).",
        risk="high",
    ),
    Capability(
        key="read_files",
        title="Read files",
        description="Read the contents of files you point it to.",
        risk="medium",
    ),
    Capability(
        key="write_files",
        title="Write & edit files",
        description="Create or modify files on disk.",
        risk="high",
    ),
    Capability(
        key="voice",
        title="Speak out loud",
        description="Use text-to-speech so Dexter can talk back, JARVIS-style.",
        risk="low",
    ),
    Capability(
        key="microphone",
        title="Listen to the microphone",
        description="Use the microphone for voice commands and the wake word.",
        risk="medium",
    ),
    Capability(
        key="network",
        title="Access the internet",
        description="Reach the OpenRouter API (the AI brain) and perform web lookups.",
        risk="medium",
    ),
]

CAP_BY_KEY: Dict[str, Capability] = {c.key: c for c in CAPABILITIES}

# Capabilities granted automatically once the user accepts the consent screen.
# High-risk ones can still be toggled off individually in the UI afterwards.
DEFAULT_GRANTED = {c.key for c in CAPABILITIES}


class PermissionManager:
    """Loads, stores and checks capability grants."""

    def __init__(self, consent_file: Path):
        self.consent_file = consent_file
        self._state: Dict[str, object] = self._load()

    # -- persistence ---------------------------------------------------------
    def _load(self) -> Dict[str, object]:
        if self.consent_file.exists():
            try:
                return json.loads(self.consent_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"accepted": False, "accepted_at": None, "grants": {}}

    def _save(self) -> None:
        self.consent_file.parent.mkdir(parents=True, exist_ok=True)
        self.consent_file.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -- consent -------------------------------------------------------------
    @property
    def has_consented(self) -> bool:
        return bool(self._state.get("accepted"))

    def accept(self, grants: Dict[str, bool] | None = None) -> None:
        """Record the one-time consent. Called when the user approves on first run."""
        resolved = {c.key: True for c in CAPABILITIES if c.key in DEFAULT_GRANTED}
        if grants:
            for k, v in grants.items():
                if k in CAP_BY_KEY:
                    resolved[k] = bool(v)
        self._state = {
            "accepted": True,
            "accepted_at": time.time(),
            "grants": resolved,
        }
        self._save()

    def reset(self) -> None:
        """Forget all consent (user asked to be prompted again)."""
        self._state = {"accepted": False, "accepted_at": None, "grants": {}}
        self._save()

    # -- grants --------------------------------------------------------------
    def is_granted(self, key: str) -> bool:
        if not self.has_consented:
            return False
        return bool(self._state.get("grants", {}).get(key, False))

    def set_grant(self, key: str, value: bool) -> None:
        if key not in CAP_BY_KEY:
            raise KeyError(f"Unknown capability: {key}")
        grants = dict(self._state.get("grants", {}))
        grants[key] = bool(value)
        self._state["grants"] = grants
        self._save()

    def grants(self) -> Dict[str, bool]:
        return dict(self._state.get("grants", {}))

    def snapshot(self) -> dict:
        """Everything the UI needs to render permission state."""
        return {
            "accepted": self.has_consented,
            "accepted_at": self._state.get("accepted_at"),
            "capabilities": [
                {
                    "key": c.key,
                    "title": c.title,
                    "description": c.description,
                    "risk": c.risk,
                    "granted": self.is_granted(c.key),
                }
                for c in CAPABILITIES
            ],
        }


class PermissionError(Exception):
    """Raised when a tool is used without the required grant."""

    def __init__(self, capability: str):
        cap = CAP_BY_KEY.get(capability)
        label = cap.title if cap else capability
        super().__init__(
            f"Permission '{label}' is not granted. Enable it in Dexter's settings to use this."
        )
        self.capability = capability
