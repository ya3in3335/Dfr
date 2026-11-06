#!/usr/bin/env python3
"""Launch Dexter Cyber.

Default: the native PySide6 desktop app.

    python run.py

Optional classic local web UI (FastAPI):

    python run.py --web

Configuration (API keys, models, voice) lives in the in-app Settings dialog, or
a ``.env`` file. You need a free OpenRouter key: https://openrouter.ai/keys
"""
from __future__ import annotations

import sys

from dexter import __app_name__, __version__
from dexter.config import settings


def _run_web() -> int:
    try:
        import uvicorn
    except ImportError:
        print("Missing deps. Run:  pip install -r requirements.txt")
        return 1
    import threading
    import webbrowser

    url = f"http://{settings.host}:{settings.port}"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"{__app_name__} (web) → {url}")
    if getattr(sys, "frozen", False):
        from dexter.server import app as fastapi_app
        uvicorn.run(fastapi_app, host=settings.host, port=settings.port, log_level="info")
    else:
        uvicorn.run("dexter.server:app", host=settings.host, port=settings.port, log_level="info")
    return 0


def main() -> int:
    if "--web" in sys.argv:
        return _run_web()
    try:
        from dexter.ui_qt.app import main as qt_main
    except ImportError as exc:
        print(f"PySide6 UI unavailable ({exc}).")
        print("Install deps:  pip install -r requirements.txt")
        print("Or run the web UI:  python run.py --web")
        return 1
    return qt_main()


if __name__ == "__main__":
    sys.exit(main())
