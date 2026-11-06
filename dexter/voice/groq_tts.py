"""Groq neural text-to-speech client.

Uses Groq's OpenAI-compatible ``/audio/speech`` endpoint. By default it speaks
with the Arabic (Saudi) Orpheus voice ``abdullah`` from the
``canopylabs/orpheus-arabic-saudi`` model, but model and voice are configurable.

The audio (WAV) is returned as raw bytes so the server can forward it to the
browser to play — no server-side audio hardware required.
"""
from __future__ import annotations

from typing import Optional

import httpx

from ..config import settings


class GroqTTSError(RuntimeError):
    pass


class GroqTTS:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = (api_key or settings.groq_api_key).strip()
        self.base_url = (base_url or settings.groq_base_url).rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def synthesize(
        self,
        text: str,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        response_format: str = "wav",
        timeout: float = 60.0,
    ) -> bytes:
        """Return spoken audio bytes for ``text``."""
        if not self.configured:
            raise GroqTTSError("No GROQ_API_KEY configured. Add it to your .env to use the Groq voice.")
        if not text.strip():
            return b""

        payload = {
            "model": model or settings.groq_tts_model,
            "voice": voice or settings.groq_voice,
            "input": text,
            "response_format": response_format,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/audio/speech"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise GroqTTSError(f"Network error reaching Groq: {exc}") from exc

        if resp.status_code == 401:
            raise GroqTTSError("Groq rejected the API key (401). Check GROQ_API_KEY.")
        if resp.status_code >= 400:
            raise GroqTTSError(f"Groq TTS error {resp.status_code}: {resp.text[:300]}")
        return resp.content
