"""Screen vision: capture the display and let a vision model describe it.

Uses ``mss`` for fast, cross-platform screen capture and ``Pillow`` to encode.
Both are optional at import time so the package still loads on a headless box.
"""
from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Optional, Tuple

from ..config import settings


def capture_available() -> bool:
    try:
        import mss  # noqa: F401
        import PIL  # noqa: F401

        return True
    except Exception:
        return False


def capture_screen(monitor: int = 0) -> bytes:
    """Capture the screen (or a monitor) and return PNG bytes.

    ``monitor=0`` captures the full virtual desktop (all monitors combined).
    """
    try:
        import mss
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Screen capture needs 'mss' and 'Pillow'. Install requirements.txt."
        ) from exc

    with mss.mss() as sct:
        mons = sct.monitors
        idx = monitor if 0 <= monitor < len(mons) else 0
        shot = sct.grab(mons[idx])
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        # Downscale very large captures so the vision model stays responsive.
        max_w = 1600
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


def save_capture(image_bytes: bytes) -> Path:
    name = f"screen-{int(time.time())}.png"
    path = settings.screenshot_dir / name
    path.write_bytes(image_bytes)
    return path


def screen_size() -> Optional[Tuple[int, int]]:
    try:
        import mss

        with mss.mss() as sct:
            m = sct.monitors[0]
            return m["width"], m["height"]
    except Exception:
        return None
