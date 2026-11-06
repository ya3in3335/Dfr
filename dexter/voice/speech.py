"""Voice output and input.

Text-to-speech uses ``pyttsx3`` — the same offline engine used by the
referenced J.A.R.V.I.S project (GauravSingh9356/J.A.R.V.I.S), so Dexter talks
back without any cloud TTS. Speech recognition uses ``SpeechRecognition`` with
the microphone, including a simple wake word ("dexter").

Both are optional: if the libraries or hardware are missing, the assistant
still works in text mode and simply reports that voice is unavailable.

TTS runs in a dedicated worker thread because pyttsx3's run loop is not
thread-safe and must own its engine.
"""
from __future__ import annotations

import queue
import threading
from typing import Optional

from ..config import settings


class Speaker:
    """Background text-to-speech worker (JARVIS-style voice output)."""

    def __init__(self):
        self._queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._available = False
        self.rate = settings.voice_rate
        self._start()

    def set_rate(self, rate: int) -> None:
        try:
            self.rate = int(rate)
        except Exception:
            pass

    def _start(self) -> None:
        try:
            import pyttsx3  # noqa: F401
        except Exception:
            self._available = False
            return
        self._available = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def available(self) -> bool:
        return self._available

    def _run(self) -> None:  # pragma: no cover - requires audio hardware
        import pyttsx3

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            if settings.voice_name:
                for voice in engine.getProperty("voices"):
                    if settings.voice_name.lower() in (voice.name or "").lower():
                        engine.setProperty("voice", voice.id)
                        break
        except Exception:
            self._available = False
            return

        while True:
            text = self._queue.get()
            if text is None:
                break
            try:
                engine.setProperty("rate", self.rate)
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass

    def say(self, text: str) -> None:
        if self._available and text:
            self._queue.put(text)

    def stop(self) -> None:
        if self._thread:
            self._queue.put(None)


class Listener:
    """One-shot microphone speech recognition (optional)."""

    def __init__(self):
        self._available = False
        try:
            import speech_recognition as sr  # noqa: F401

            self._sr = sr
            self._recognizer = sr.Recognizer()
            self._available = True
        except Exception:
            self._sr = None
            self._recognizer = None

    @property
    def available(self) -> bool:
        return self._available

    def listen_once(self, timeout: float = 6.0, phrase_limit: float = 10.0) -> Optional[str]:  # pragma: no cover
        if not self._available:
            return None
        sr = self._sr
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            return self._recognizer.recognize_google(audio)
        except Exception:
            return None


def strip_wake_word(text: str, wake: str = "dexter") -> Optional[str]:
    """Return the command after the wake word, or None if absent."""
    if not text:
        return None
    low = text.lower()
    if wake in low:
        idx = low.index(wake) + len(wake)
        return text[idx:].strip(" ,.:;-") or ""
    return None
