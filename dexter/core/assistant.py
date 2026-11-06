"""Assistant controller — the framework-agnostic brain wiring.

Holds the long-lived singletons (LLM, permissions, memory, tools, voice) and
exposes a simple async ``process()`` used by the PySide6 desktop UI. It knows
nothing about Qt or HTTP, so it can be driven from any front end.
"""
from __future__ import annotations

import platform
from typing import Awaitable, Callable, Dict

from ..config import settings
from .agent import DexterAgent
from .llm import OpenRouterClient
from .memory import Memory
from .permissions import PermissionManager
from ..tools.registry import ToolRegistry, capability_runtime_status
from ..voice.groq_tts import GroqTTS, GroqTTSError
from ..voice.speech import Speaker

Emit = Callable[[Dict[str, object]], Awaitable[None]]


class Assistant:
    def __init__(self):
        self.permissions = PermissionManager(settings.consent_file)
        self.llm = OpenRouterClient()
        self.memory = Memory(settings.memory_file)
        self.tools = ToolRegistry(self.permissions, self.llm)
        self.speaker = Speaker()
        self.groq_tts = GroqTTS()
        self.agent = DexterAgent(
            llm=self.llm,
            tools=self.tools,
            memory=self.memory,
            env_note=f"{platform.system()} {platform.release()} ({platform.machine()})",
        )
        self.running = 0

    # -- settings ------------------------------------------------------------
    def apply_settings(self, values: dict) -> None:
        """Persist edited settings and rebuild clients that captured keys."""
        settings.update_settings(**values)
        self.llm = OpenRouterClient()
        self.groq_tts = GroqTTS()
        self.tools.llm = self.llm
        self.agent.llm = self.llm
        try:
            self.speaker.set_rate(settings.voice_rate)
        except Exception:
            pass

    def state(self) -> dict:
        return {
            "has_api_key": settings.has_api_key,
            "has_groq_key": settings.has_groq_key,
            "text_model": settings.text_model,
            "vision_model": settings.vision_model,
            "voice_engine": settings.voice_engine,
            "wake_word": settings.wake_word,
            "runtime": capability_runtime_status(),
            "consent": self.permissions.snapshot(),
            "tasks": self.tools.tasks,
        }

    # -- speech --------------------------------------------------------------
    async def speak(self, text: str, emit: Emit) -> None:
        if not text or not self.permissions.is_granted("voice"):
            return
        if settings.voice_engine == "groq" and self.groq_tts.configured:
            try:
                audio = await self.groq_tts.synthesize(text)
                if audio:
                    await emit({"type": "audio", "wav": audio})
                    return
            except GroqTTSError as exc:
                await emit({"type": "error", "message": f"Groq voice failed: {exc}"})
        if self.speaker.available:
            self.speaker.say(text)
            await emit({"type": "spoke", "text": text})

    # -- main entry ----------------------------------------------------------
    async def process(self, text: str, emit: Emit) -> str:
        if not self.permissions.has_consented:
            await emit({"type": "error", "message": "Please accept the first-run authorization first."})
            return ""
        self.running += 1
        await emit({"type": "status", "state": "thinking", "running": self.running})
        try:
            final = await self.agent.handle(text, emit)
            await self.speak(final, emit)
            return final
        finally:
            self.running -= 1
            await emit({"type": "status", "state": "idle", "running": self.running})
