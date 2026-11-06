"""OpenRouter client (OpenAI-compatible chat completions).

Works with the free models on OpenRouter (the ``:free`` variants). Supports
plain text as well as multimodal messages carrying an image, which Dexter uses
to let the model "see" the screen.
"""
from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings


class LLMError(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.api_key = (api_key or settings.openrouter_api_key).strip()
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Optional attribution headers recommended by OpenRouter.
            "HTTP-Referer": settings.app_referer,
            "X-Title": settings.app_title,
        }

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1536,
        response_json: bool = False,
    ) -> str:
        """Send a chat completion request and return the assistant text."""
        if not self.configured:
            raise LLMError(
                "No OpenRouter API key configured. Set OPENROUTER_API_KEY in your .env file "
                "(get a free key at https://openrouter.ai/keys)."
            )

        payload: Dict[str, Any] = {
            "model": model or settings.text_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_json:
            payload["response_format"] = {"type": "json_object"}

        url = f"{self.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise LLMError(f"Network error reaching OpenRouter: {exc}") from exc

        if resp.status_code == 401:
            raise LLMError("OpenRouter rejected the API key (401). Check OPENROUTER_API_KEY.")
        if resp.status_code == 402:
            raise LLMError(
                "OpenRouter returned 402 (payment required). The selected model may not be free; "
                "pick a ':free' model in your .env."
            )
        if resp.status_code == 429:
            raise LLMError("Rate limited by OpenRouter (429). Wait a moment and try again.")
        if resp.status_code >= 400:
            raise LLMError(f"OpenRouter error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected response shape from OpenRouter: {data}") from exc

    async def chat_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        """Ask a vision-capable model about an image (e.g. a screenshot)."""
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        messages: List[Dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})
        return await self.chat(
            messages,
            model=model or settings.vision_model,
            temperature=0.2,
            max_tokens=max_tokens,
        )
