#!/usr/bin/env python3
"""Launch Dexter Cyber.

Starts the local server and opens the JARVIS-style UI in your browser.

    python run.py

Configuration lives in a ``.env`` file (copy ``.env.example``). You need a free
OpenRouter API key: https://openrouter.ai/keys
"""
from __future__ import annotations

import sys
import threading
import webbrowser

from dexter import __app_name__, __version__
from dexter.config import settings


BANNER = r"""
   ____            _              ____      _
  |  _ \  _____  _| |_ ___ _ __  / ___|   _| |__   ___ _ __
  | | | |/ _ \ \/ / __/ _ \ '__|| |  | | | | '_ \ / _ \ '__|
  | |_| |  __/>  <| ||  __/ |   | |__| |_| | |_) |  __/ |
  |____/ \___/_/\_\\__\___|_|    \____\__, |_.__/ \___|_|
                                      |___/
"""


def main() -> int:
    print(BANNER)
    print(f"  {__app_name__} v{__version__}")
    print(f"  UI:    http://{settings.host}:{settings.port}")
    print(f"  Brain: {settings.text_model}")
    print(f"  Vision:{settings.vision_model}")
    print(f"  Data:  {settings.home}")
    if not settings.has_api_key:
        print("\n  ⚠  No OPENROUTER_API_KEY set. Copy .env.example to .env and add a free key")
        print("      from https://openrouter.ai/keys — the UI will load but the brain is offline.\n")

    try:
        import uvicorn
    except ImportError:
        print("\n  Missing dependencies. Run:  pip install -r requirements.txt\n")
        return 1

    url = f"http://{settings.host}:{settings.port}"
    threading.Timer(1.2, lambda: _open(url)).start()

    uvicorn.run("dexter.server:app", host=settings.host, port=settings.port, log_level="info")
    return 0


def _open(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
