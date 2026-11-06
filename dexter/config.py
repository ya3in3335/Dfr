"""Central configuration for Dexter Cyber.

Values come from environment variables (optionally loaded from a local
``.env`` file). Nothing here is secret by itself; the API key is only ever
read from the environment and never written to the repo.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def resource_path(rel: str) -> Path:
    """Resolve a bundled resource path for both source and frozen (PyInstaller) runs.

    When packaged into a one-file executable, data files are unpacked to a temp
    directory exposed as ``sys._MEIPASS``. In a normal source checkout we resolve
    relative to the project root (the parent of the ``dexter`` package).
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / rel
    return Path(__file__).resolve().parent.parent / rel


try:
    from dotenv import load_dotenv

    # Load .env from the current working directory (source runs)…
    load_dotenv()
    # …and, when running as a packaged .exe, also look next to the executable.
    if getattr(sys, "frozen", False):
        _exe_env = Path(sys.executable).resolve().parent / ".env"
        if _exe_env.exists():
            load_dotenv(_exe_env, override=False)
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

    # Voice engine: "system" (offline pyttsx3, played on the host) or
    # "groq" (cloud neural TTS, streamed to the browser to play).
    voice_engine: str = field(default_factory=lambda: os.getenv("DEXTER_VOICE_ENGINE", "system").strip().lower())

    # Groq neural TTS (optional second voice option).
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip())
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_tts_model: str = field(
        default_factory=lambda: os.getenv("DEXTER_GROQ_TTS_MODEL", "canopylabs/orpheus-arabic-saudi").strip()
    )
    groq_voice: str = field(default_factory=lambda: os.getenv("DEXTER_GROQ_VOICE", "abdullah").strip())

    # Wake word for always-on listening (comma-separated accepts several).
    wake_word: str = field(default_factory=lambda: os.getenv("DEXTER_WAKE_WORD", "dexter").strip().lower())

    # Human-readable attribution sent to OpenRouter (optional, helps rankings).
    app_title: str = "Dexter Cyber"
    app_referer: str = "https://localhost/dexter-cyber"

    # Fields the user can edit from the Settings dialog and have persisted.
    _PERSIST = (
        "openrouter_api_key", "groq_api_key", "text_model", "vision_model",
        "voice_engine", "voice_enabled", "voice_rate", "groq_tts_model",
        "groq_voice", "wake_word",
    )

    def __post_init__(self) -> None:
        # Apply persisted preferences (GUI-entered values override env defaults).
        try:
            import json

            if self.prefs_file.exists():
                prefs = json.loads(self.prefs_file.read_text(encoding="utf-8"))
                for k in self._PERSIST:
                    if k in prefs and prefs[k] is not None:
                        setattr(self, k, prefs[k])
        except Exception:
            pass

    def update_settings(self, **values) -> None:
        """Apply and persist edited settings (from the Settings dialog)."""
        for k, v in values.items():
            if k in self._PERSIST and v is not None:
                setattr(self, k, v.strip() if isinstance(v, str) else v)
        self.save_prefs()

    def save_prefs(self) -> None:
        import json

        try:
            self.prefs_file.write_text(
                json.dumps(
                    {k: getattr(self, k) for k in self._PERSIST},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    @property
    def prefs_file(self) -> Path:
        return self.home / "prefs.json"

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

    @property
    def has_groq_key(self) -> bool:
        return bool(self.groq_api_key)


settings = Settings()
