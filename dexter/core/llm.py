"""OpenRouter client with multi-model fallback (free models working together).

A chat request tries a chain of free models in order; on rate-limit (429),
unavailability (404 "unavailable for free"), server error, or an empty reply it
moves to the next model automatically. A genuine auth error (401) stops early.
Supports multimodal messages carrying an image for screen vision.
"""
from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings


class LLMError(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 120.0):
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
            "HTTP-Referer": settings.app_referer,
            "X-Title": settings.app_title,
        }

    async def _request(self, model: str, messages, temperature, max_tokens, response_json) -> str:
        payload: Dict[str, Any] = {
            "model": model,
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
            raise LLMError(f"network: {exc}") from exc

        if resp.status_code == 401:
            raise LLMError("OpenRouter rejected the API key (401). Check your OpenRouter key in Settings.")
        if resp.status_code == 402:
            raise LLMError(f"{model}: 402 (not free)")
        if resp.status_code == 429:
            raise LLMError(f"{model}: rate limited (429)")
        if resp.status_code >= 400:
            raise LLMError(f"{model}: {resp.status_code} {resp.text[:200]}")
        try:
            data = resp.json()
            return data["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError(f"{model}: bad response ({exc})") from exc

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        models: Optional[List[str]] = None,
        temperature: float = 0.3,
        max_tokens: int = 1536,
        response_json: bool = False,
    ) -> str:
        """Try a chain of models; return the first non-empty reply."""
        if not self.configured:
            raise LLMError(
                "No OpenRouter API key set. Open Settings and paste your key "
                "(starts with sk-or-v1-…) from https://openrouter.ai/keys."
            )
        chain = [model] if model else (models or settings.text_chain())
        last: Optional[LLMError] = None
        for mdl in chain:
            try:
                content = await self._request(mdl, messages, temperature, max_tokens, response_json)
                if content and content.strip():
                    return content
                last = LLMError(f"{mdl}: empty response")
            except LLMError as exc:
                if "(401)" in str(exc):
                    raise                      # auth error won't differ per model
                last = exc
                continue
        raise last or LLMError("No model returned a response.")

    async def chat_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
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
        chain = [model] if model else settings.vision_chain()
        return await self.chat(messages, models=chain, temperature=0.2, max_tokens=max_tokens)
