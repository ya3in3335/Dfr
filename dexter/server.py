"""Dexter Cyber local server.

Serves the JARVIS-style web UI and exposes a small API plus a WebSocket that
streams the agent's live reasoning/actions. Everything runs locally on the
user's machine (default 127.0.0.1) — the UI is just a comfortable front end for
a local process, not a hosted service.
"""
from __future__ import annotations

import json
import platform
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __app_name__, __version__
from .config import resource_path, settings
from .core.agent import DexterAgent
from .core.llm import OpenRouterClient
from .core.memory import Memory
from .core.permissions import CAPABILITIES, PermissionManager
from .tools.registry import ToolRegistry, capability_runtime_status
from .voice.speech import Speaker

WEB_DIR = resource_path("dexter/web")


class DexterApp:
    """Holds the long-lived singletons for one running assistant."""

    def __init__(self):
        self.permissions = PermissionManager(settings.consent_file)
        self.llm = OpenRouterClient()
        self.memory = Memory(settings.memory_file)
        self.tools = ToolRegistry(self.permissions, self.llm)
        self.speaker = Speaker()
        self.agent = DexterAgent(
            llm=self.llm,
            tools=self.tools,
            memory=self.memory,
            env_note=f"{platform.system()} {platform.release()} ({platform.machine()})",
        )

    def state(self) -> dict:
        return {
            "app": __app_name__,
            "version": __version__,
            "has_api_key": settings.has_api_key,
            "text_model": settings.text_model,
            "vision_model": settings.vision_model,
            "voice_available": self.speaker.available and self.permissions.is_granted("voice"),
            "runtime": capability_runtime_status(),
            "consent": self.permissions.snapshot(),
        }


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
    """First-run consent. ``payload['grants']`` optionally overrides defaults."""
    grants = payload.get("grants") if isinstance(payload, dict) else None
    dexter.permissions.accept(grants)
    return JSONResponse(dexter.state())


@app.post("/api/permission")
async def api_permission(payload: dict) -> JSONResponse:
    """Toggle one capability on/off after consent."""
    key = payload.get("key")
    value = bool(payload.get("value"))
    try:
        dexter.permissions.set_grant(key, value)
    except KeyError:
        return JSONResponse({"error": f"unknown capability: {key}"}, status_code=400)
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
    await websocket.accept()

    async def emit(event: dict) -> None:
        await websocket.send_text(json.dumps(event, ensure_ascii=False))

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
                await emit({"type": "error", "message": "Please accept the first-run consent before talking to Dexter."})
                continue

            await emit({"type": "status", "state": "thinking"})
            final = await dexter.agent.handle(user_text, emit)
            await emit({"type": "status", "state": "idle"})

            # Speak the final answer if voice is granted and available.
            if final and dexter.permissions.is_granted("voice") and dexter.speaker.available:
                dexter.speaker.say(final)
                await emit({"type": "spoke", "text": final})
    except WebSocketDisconnect:
        return


# Mount static assets last so API routes take precedence.
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
