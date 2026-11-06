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
from pathlib import Path

from dexter import __app_name__, __version__
from dexter.config import settings


def _log_crash(tb: str) -> None:
    """Write a startup crash to a log file so a windowed build is debuggable."""
    import datetime
    import tempfile

    stamp = datetime.datetime.now().isoformat()
    body = f"{stamp}\n{__app_name__} v{__version__}\n\n{tb}\n"
    for path in (Path.cwd() / "DexterCyber-error.log",
                 Path(tempfile.gettempdir()) / "DexterCyber-error.log"):
        try:
            path.write_text(body, encoding="utf-8")
        except Exception:
            pass
    print(body)


class _Tee:
    """Write to both the console and a log file (handles a missing stream)."""

    def __init__(self, *streams):
        self._streams = [s for s in streams if s is not None]

    def write(self, data):
        for s in self._streams:
            try:
                s.write(data); s.flush()
            except Exception:
                pass

    def flush(self):
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass


def _install_diagnostics():
    """Capture ALL output + fatal crashes to a log, so a flash-and-close build
    still tells us exactly why it exited."""
    try:
        import faulthandler
        import platform
        import tempfile

        log_path = Path(tempfile.gettempdir()) / "DexterCyber-boot.log"
        f = open(log_path, "w", encoding="utf-8", buffering=1)
        f.write(f"{__app_name__} v{__version__}\nPython {sys.version}\n{platform.platform()}\n"
                f"frozen={getattr(sys, 'frozen', False)}\n--- boot ---\n")
        faulthandler.enable(f)                      # dumps even hard crashes
        sys.stdout = _Tee(sys.stdout, f)
        sys.stderr = _Tee(sys.stderr, f)
        return log_path
    except Exception:
        return None


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
    _install_diagnostics()
    if "--web" in sys.argv:
        return _run_web()
    try:
        from dexter.ui_qt.app import main as qt_main
    except ImportError as exc:
        print(f"PySide6 UI unavailable ({exc}).")
        print("Install deps:  pip install -r requirements.txt")
        print("Or run the web UI:  python run.py --web")
        return 1
    try:
        return qt_main()
    except Exception:
        import traceback
        _log_crash(traceback.format_exc())
        try:
            input("\nDexter hit an error on startup. Details above and in "
                  "DexterCyber-error.log. Press Enter to close…")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
