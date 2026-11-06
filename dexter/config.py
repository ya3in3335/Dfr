"""Central configuration for Dexter Cyber.

Values come from environment variables (optionally loaded from a local
``.env`` file). Nothing here is secret by itself; the API key is only ever
read from the environment and never written to the repo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _home() -> Path:
    override = os.getenv("DEXTER_HOME")
    base = Path(override).expanduser() if override else Path.home() / ".dexter_cyber"
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass
class Settings:
    """Runtime settings resolved from the environment."""

    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "").strip())
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    text_model: str = field(
        default_factory=lambda: os.getenv("DEXTER_TEXT_MODEL", "meta-llama/llama-3.3-70b-instruct:free").strip()
    )
    vision_model: str = field(
        default_factory=lambda: os.getenv("DEXTER_VISION_MODEL", "google/gemini-2.0-flash-exp:free").strip()
    )

    home: Path = field(default_factory=_home)

    host: str = field(default_factory=lambda: os.getenv("DEXTER_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("DEXTER_PORT", "8787")))

    voice_enabled: bool = field(default_factory=lambda: os.getenv("DEXTER_VOICE", "1") == "1")
    voice_name: str = field(default_factory=lambda: os.getenv("DEXTER_VOICE_NAME", "").strip())
    voice_rate: int = field(default_factory=lambda: int(os.getenv("DEXTER_VOICE_RATE", "175")))

    # Human-readable attribution sent to OpenRouter (optional, helps rankings).
    app_title: str = "Dexter Cyber"
    app_referer: str = "https://localhost/dexter-cyber"

    @property
    def consent_file(self) -> Path:
        return self.home / "consent.json"

    @property
    def memory_file(self) -> Path:
        return self.home / "memory.json"

    @property
    def log_file(self) -> Path:
        return self.home / "dexter.log"

    @property
    def screenshot_dir(self) -> Path:
        d = self.home / "screenshots"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def has_api_key(self) -> bool:
        return bool(self.openrouter_api_key)


settings = Settings()
