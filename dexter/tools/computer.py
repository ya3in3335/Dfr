"""Direct computer control: mouse and keyboard.

Backed by ``pyautogui``. Imported lazily so the package loads on machines
without a display. A small failsafe is enabled: slamming the cursor into the
top-left corner aborts automation (pyautogui's built-in kill switch).
"""
from __future__ import annotations

from typing import Optional, Tuple

_pyautogui = None


def _gui():
    global _pyautogui
    if _pyautogui is None:
        try:
            import pyautogui

            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05
            _pyautogui = pyautogui
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Computer control needs 'pyautogui' and a graphical display. "
                "On Linux you may also need python3-tk/python3-xlib."
            ) from exc
    return _pyautogui


def control_available() -> bool:
    try:
        _gui()
        return True
    except Exception:
        return False


def position() -> Tuple[int, int]:
    x, y = _gui().position()
    return int(x), int(y)


def move_to(x: int, y: int, duration: float = 0.25) -> str:
    _gui().moveTo(x, y, duration=duration)
    return f"Moved cursor to ({x}, {y})."


def click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1) -> str:
    g = _gui()
    if x is not None and y is not None:
        g.click(x=x, y=y, button=button, clicks=clicks)
        return f"Clicked {button} x{clicks} at ({x}, {y})."
    g.click(button=button, clicks=clicks)
    return f"Clicked {button} x{clicks} at current position."


def double_click(x: Optional[int] = None, y: Optional[int] = None) -> str:
    _gui().doubleClick(x=x, y=y)
    return "Double-clicked."


def type_text(text: str, interval: float = 0.02) -> str:
    _gui().write(text, interval=interval)
    return f"Typed {len(text)} characters."


def press_key(key: str) -> str:
    _gui().press(key)
    return f"Pressed '{key}'."


def hotkey(*keys: str) -> str:
    _gui().hotkey(*keys)
    return f"Pressed hotkey: {'+'.join(keys)}."


def scroll(amount: int) -> str:
    _gui().scroll(amount)
    return f"Scrolled {amount}."
