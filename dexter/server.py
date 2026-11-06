"""Dexter Cyber local server.

Serves the JARVIS-style web UI and exposes a small API plus a WebSocket that
streams the agent's live reasoning/actions. Everything runs locally on the
user's machine (default 127.0.0.1).

Highlights
----------
* **Broadcast bus** — events (thoughts, actions, cards, audio) go to every open
  UI, so results from a background/wake-word command show up too.
* **Multi-tasking** — each incoming command runs as its own asyncio task, so
  several commands (typed or spoken) can run concurrently without blocking.
* **Two voices** — offline system TTS (played on the host) or Groq neural TTS
  (streamed to the browser to play).
"""
from __future__ import annotations

import asyncio
import base64
import json
import platform
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __app_name__, __version__
from .config import resource_path, settings
from .core.agent import DexterAgent
from .core.llm import OpenRouterClient
from .core.memory import Memory
from .core.permissions import PermissionManager
from .tools.registry import ToolRegistry, capability_runtime_status
from .voice.groq_tts import GroqTTS, GroqTTSError
from .voice.speech import Speaker

WEB_DIR = resource_path("dexter/web")


class ConnectionManager:
    """Tracks open WebSocket clients and broadcasts events to all of them."""

    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def broadcast(self, event: dict) -> None:
        dead = []
        text = json.dumps(event, ensure_ascii=False)
        for ws in list(self.active):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.discard(ws)


class DexterApp:
    """Holds the long-lived singletons for one running assistant."""

    def __init__(self):
        self.permissions = PermissionManager(settings.consent_file)
        self.llm = OpenRouterClient()
        self.memory = Memory(settings.memory_file)
        self.tools = ToolRegistry(self.permissions, self.llm)
        self.speaker = Speaker()
        self.groq_tts = GroqTTS()
        self.manager = ConnectionManager()
        self.agent = DexterAgent(
            llm=self.llm,
            tools=self.tools,
            memory=self.memory,
            env_note=f"{platform.system()} {platform.release()} ({platform.machine()})",
        )
        self._running = 0  # number of in-flight commands (multi-tasking)

    def state(self) -> dict:
        return {
            "app": __app_name__,
            "version": __version__,
            "has_api_key": settings.has_api_key,
            "has_groq_key": settings.has_groq_key,
            "text_model": settings.text_model,
            "vision_model": settings.vision_model,
            "voice_engine": settings.voice_engine,
            "voice_engines": [
                {"key": "system", "label": "System voice (offline)", "available": self.speaker.available},
                {"key": "groq", "label": f"Groq neural ({settings.groq_voice})", "available": settings.has_groq_key},
            ],
            "wake_word": settings.wake_word,
            "runtime": capability_runtime_status(),
            "consent": self.permissions.snapshot(),
            "tasks": self.tools.tasks,
        }

    async def speak(self, text: str) -> None:
        """Voice the final answer via the selected engine."""
        if not text or not self.permissions.is_granted("voice"):
            return
        engine = settings.voice_engine
        if engine == "groq" and self.groq_tts.configured:
            try:
                audio = await self.groq_tts.synthesize(text)
                if audio:
                    b64 = base64.b64encode(audio).decode("ascii")
                    await self.manager.broadcast({"type": "audio", "format": "wav", "data": b64})
                    return
            except GroqTTSError as exc:
                await self.manager.broadcast({"type": "error", "message": f"Groq voice failed: {exc}"})
                # fall through to system voice as a fallback
        if self.speaker.available:
            self.speaker.say(text)
            await self.manager.broadcast({"type": "spoke", "text": text})

    async def process_command(self, user_text: str) -> None:
        """Run one command end-to-end, broadcasting all events (multi-tasking)."""
        self._running += 1
        await self.manager.broadcast({"type": "status", "state": "thinking", "running": self._running})
        try:
            final = await self.agent.handle(user_text, self.manager.broadcast)
            await self.speak(final)
        finally:
            self._running -= 1
            await self.manager.broadcast({"type": "status", "state": "idle", "running": self._running})


app = FastAPI(title=__app_name__, version=__version__)
dexter = DexterApp()


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((WEB_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/state")
async def api_state() -> JSONResponse:
    return JSONResponse(dexter.state())


@app.post("/api/consent")
async def api_consent(payload: dict) -> JSONResponse:
    grants = payload.get("grants") if isinstance(payload, dict) else None
    dexter.permissions.accept(grants)
    return JSONResponse(dexter.state())


@app.post("/api/permission")
async def api_permission(payload: dict) -> JSONResponse:
    key = payload.get("key")
    value = bool(payload.get("value"))
    try:
        dexter.permissions.set_grant(key, value)
    except KeyError:
        return JSONResponse({"error": f"unknown capability: {key}"}, status_code=400)
    return JSONResponse(dexter.state())


@app.post("/api/voice-engine")
async def api_voice_engine(payload: dict) -> JSONResponse:
    engine = (payload.get("engine") or "").strip().lower()
    if engine not in ("system", "groq"):
        return JSONResponse({"error": "engine must be 'system' or 'groq'"}, status_code=400)
    settings.voice_engine = engine
    settings.save_prefs()
    return JSONResponse(dexter.state())


@app.post("/api/reset-consent")
async def api_reset_consent() -> JSONResponse:
    dexter.permissions.reset()
    return JSONResponse(dexter.state())


@app.post("/api/clear-memory")
async def api_clear_memory() -> JSONResponse:
    dexter.memory.clear()
    return JSONResponse({"ok": True})


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await dexter.manager.connect(websocket)
    # Hand the freshly-connected client the current task board.
    try:
        await websocket.send_text(json.dumps({"type": "sync", "tasks": dexter.tools.tasks}, ensure_ascii=False))
    except Exception:
        pass

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                msg = {"type": "chat", "text": raw}

            if msg.get("type") != "chat":
                continue

            user_text = (msg.get("text") or "").strip()
            if not user_text:
                continue

            if not dexter.permissions.has_consented:
                await websocket.send_text(json.dumps(
                    {"type": "error", "message": "Please accept the first-run consent before talking to Dexter."}
                ))
                continue

            # Multi-tasking: run each command concurrently without blocking the
            # receive loop, so new (typed or spoken) commands can start anytime.
            asyncio.create_task(dexter.process_command(user_text))
    except WebSocketDisconnect:
        dexter.manager.disconnect(websocket)
    except Exception:
        dexter.manager.disconnect(websocket)


# Mount static assets last so API routes take precedence.
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
