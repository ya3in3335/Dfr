"""Threading bridges between the async brain and the Qt UI.

* ``AsyncLoop`` runs an asyncio event loop in its own thread; the agent's
  network calls live here so the UI never blocks.
* ``Bridge`` relays agent events to the GUI thread via a Qt signal (queued,
  thread-safe).
* ``WakeListener`` optionally listens on the microphone in the background for
  the wake word and emits recognised commands.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal


class Bridge(QObject):
    event = Signal(dict)  # agent events → GUI


class AsyncLoop(QThread):
    def __init__(self):
        super().__init__()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._ready = threading.Event()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        self.loop.run_forever()

    def submit(self, coro):
        self._ready.wait(timeout=5)
        if self.loop is None:
            raise RuntimeError("event loop not ready")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)


class MicLevelMonitor(QThread):
    """Emits the live microphone loudness (0..1) so the orb reacts to sound.

    Uses ``sounddevice`` if available (optional dependency). If it is not
    installed, the thread simply exits and the orb falls back to its synthetic
    listening animation.
    """

    level = Signal(float)

    def __init__(self):
        super().__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            import sounddevice as sd
        except Exception:
            return
        import array

        block = 1024
        rate = 16000
        try:
            stream = sd.RawInputStream(samplerate=rate, blocksize=block,
                                       channels=1, dtype="int16")
            stream.start()
        except Exception:
            return
        try:
            while not self._stop.is_set():
                data, _ = stream.read(block)
                samples = array.array("h")
                samples.frombytes(bytes(data))
                if not samples:
                    continue
                rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
                self.level.emit(min(1.0, rms / 6000.0))  # ~normalise to 0..1
        except Exception:
            pass
        finally:
            try:
                stream.stop(); stream.close()
            except Exception:
                pass


class WakeListener(QThread):
    """Always-on background wake-word listener (optional; needs a microphone)."""

    command = Signal(str)
    state = Signal(str)   # "listening" | "heard" | "error" | "off"

    def __init__(self, wake_word: str = "dexter"):
        super().__init__()
        self.wake_word = (wake_word or "dexter").lower()
        self._stop = threading.Event()
        self._available = False
        try:
            import speech_recognition  # noqa: F401
            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def stop(self):
        self._stop.set()

    def run(self):
        if not self._available:
            self.state.emit("error")
            return
        import speech_recognition as sr

        try:
            rec = sr.Recognizer()
            mic = sr.Microphone()
            with mic as source:
                rec.adjust_for_ambient_noise(source, duration=0.5)
        except Exception:
            self.state.emit("error")
            return

        self.state.emit("listening")
        while not self._stop.is_set():
            try:
                with mic as source:
                    audio = rec.listen(source, timeout=4, phrase_time_limit=8)
                text = rec.recognize_google(audio)
            except Exception:
                continue
            low = text.lower()
            if self.wake_word in low:
                self.state.emit("heard")
                cmd = text[low.index(self.wake_word) + len(self.wake_word):].strip(" ,.:;-")
                if cmd:
                    self.command.emit(cmd)
        self.state.emit("off")
