"""The Dexter orb — a fine, dense particle ring with mood-driven motion.

Thousands of tiny points sit on a very thin ring (nanometre-fine look). The
ring's motion changes with Dexter's "mood": calm, listening, thinking, speaking,
happy, alert — each a distinct animation (rotation speed, wave lobes, amplitude,
thickness, spray, brightness, breathing). Moods ease into one another smoothly,
and audio level / pulses modulate the current mood. Drawn additively on black.

Public API: ``set_state``, ``set_mood``, ``flash_mood``, ``set_caption``,
``set_level``, ``pulse``.
"""
from __future__ import annotations

import math
import random
import time

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QRadialGradient, QFont
from PySide6.QtWidgets import QWidget

CAPTIONS = {
    "idle": "Hi, how can I help you …",
    "listening": "Listening …",
    "thinking": "Processing …",
    "speaking": "Speaking …",
}

# Each mood is a distinct animation personality.
# spin: rotation speed · amp: wave height · lobes: wave count · thick: band width
# spray: outward wisp strength · bright: glow · breath: in/out breathing
MOODS = {
    "calm":      dict(spin=0.07, amp=0.018, lobes=2.0, thick=0.020, spray=0.5, bright=0.85, breath=0.012),
    "listening": dict(spin=0.12, amp=0.045, lobes=3.0, thick=0.045, spray=0.9, bright=1.05, breath=0.020),
    "thinking":  dict(spin=0.55, amp=0.040, lobes=5.0, thick=0.060, spray=1.2, bright=1.00, breath=0.010),
    "speaking":  dict(spin=0.16, amp=0.110, lobes=4.0, thick=0.075, spray=1.4, bright=1.15, breath=0.016),
    "happy":     dict(spin=0.30, amp=0.075, lobes=6.0, thick=0.055, spray=1.7, bright=1.25, breath=0.022),
    "alert":     dict(spin=0.02, amp=0.030, lobes=9.0, thick=0.035, spray=0.8, bright=1.10, breath=0.006),
}
STATE_MOOD = {"idle": "calm", "listening": "listening", "thinking": "thinking", "speaking": "speaking"}

C_R, C_G, C_B = 205, 212, 222          # cool light-gray glow (monochrome)
N_PARTICLES = 2300


class OrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self._phase = 0.0
        self._rot = 0.0
        self._intensity = 0.25
        self._target = 0.25
        self._level = 0.0
        self._state = "idle"
        self._mood = "calm"
        self._flash = None            # (mood, until_ts)
        self._p = dict(MOODS["calm"])  # current (eased) params
        self._caption = CAPTIONS["idle"]
        self._pulses: list[float] = []
        self._particles = self._build_particles()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _build_particles(self):
        rnd = random.Random(11)
        parts = []
        for i in range(N_PARTICLES):
            # gaussian radial offset keeps most points on a thin line
            rf = max(-1.0, min(1.0, rnd.gauss(0, 0.5)))
            parts.append({
                "a": rnd.uniform(0, 2 * math.pi),
                "rf": rf,
                "ph": rnd.uniform(0, 2 * math.pi),
                "jit": rnd.uniform(-1, 1),
                "spray": rnd.random() < 0.10,
                "sz": rnd.uniform(0.5, 1.15),
                "b": rnd.uniform(0.5, 1.0),
                "sp": rnd.uniform(0.8, 1.3),
            })
        return parts

    # -- public API ----------------------------------------------------------
    def set_state(self, state: str):
        self._state = state
        self._mood = STATE_MOOD.get(state, self._mood)
        self._target = {"idle": 0.25, "listening": 0.8, "thinking": 0.6, "speaking": 0.95}.get(state, 0.25)
        self._caption = CAPTIONS.get(state, self._caption)

    def set_mood(self, mood: str):
        if mood in MOODS:
            self._mood = mood

    def flash_mood(self, mood: str, seconds: float = 2.0):
        """Briefly express a feeling (e.g. happy / alert), then revert."""
        if mood in MOODS:
            self._flash = (mood, time.monotonic() + seconds)

    def set_caption(self, text: str):
        self._caption = text

    def set_level(self, level: float):
        self._level = max(self._level * 0.6, min(1.0, level))

    def pulse(self):
        self._pulses.append(time.monotonic())
        self._target = max(self._target, 0.95)

    # -- animation -----------------------------------------------------------
    def _active_mood(self) -> str:
        if self._flash:
            mood, until = self._flash
            if time.monotonic() < until:
                return mood
            self._flash = None
        return self._mood

    def _tick(self):
        tgt = MOODS[self._active_mood()]
        for k, v in tgt.items():
            self._p[k] += (v - self._p[k]) * 0.07     # smooth mood transitions
        reactive = max(self._target, self._level)
        self._intensity += (reactive - self._intensity) * 0.10
        self._level *= 0.9
        self._phase += 0.016 + self._intensity * 0.05
        self._rot += self._p["spin"] * 0.016
        now = time.monotonic()
        self._pulses = [t for t in self._pulses if now - t < 1.2]
        self.update()

    def _pulse_amp(self) -> float:
        now = time.monotonic()
        a = 0.0
        for t in self._pulses:
            prog = (now - t) / 1.2
            if 0 <= prog <= 1:
                a = max(a, math.sin(prog * math.pi))
        return a

    # -- painting ------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - h * 0.02
        R = min(w, h) / 2 * 0.74
        mp = self._p
        t = self._phase
        inten = min(1.4, self._intensity + 0.5 * self._pulse_amp())
        squash = 0.97

        self._core(p, cx, cy, R, inten, mp["bright"])

        breath = 1.0 + mp["breath"] * math.sin(t * 0.9)
        R0 = R * 0.985 * breath
        thick = R * mp["thick"]
        wave_amp = R * mp["amp"] * (0.45 + 0.9 * inten)
        lobes = mp["lobes"]

        p.setCompositionMode(QPainter.CompositionMode_Plus)
        p.setPen(Qt.NoPen)
        for pt in self._particles:
            a = pt["a"] + self._rot
            disp = (math.sin(lobes * a + t * pt["sp"] + pt["ph"])
                    + 0.5 * math.sin((lobes + 3) * a - t * 1.1)
                    + 0.3 * math.sin((lobes + 6) * a + t * 0.6 + pt["ph"]))
            spray = (mp["spray"] * 1.6) if pt["spray"] else mp["spray"]
            rr = R0 + pt["rf"] * thick + disp * wave_amp * (0.5 + 0.5 * spray) + pt["jit"] * R * 0.006
            x = cx + rr * math.cos(a)
            y = cy + rr * math.sin(a) * squash

            peak = 0.5 + 0.5 * (disp / 1.8)
            bright = max(0.0, min(1.0, pt["b"] * (0.4 + 0.7 * peak) * mp["bright"]))
            p.setBrush(QColor(C_R, C_G, C_B, int(40 + 150 * bright)))
            s = pt["sz"] * (1.0 + 0.35 * bright)
            p.drawEllipse(QPointF(x, y), s, s)
            if bright > 0.9:
                p.setBrush(QColor(236, 239, 243, 150))
                p.drawEllipse(QPointF(x, y), s * 0.45, s * 0.45)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        self._caption_text(p, cx, cy + R + min(w, h) * 0.06, R * 2)
        p.end()

    def _core(self, p, cx, cy, R, inten, bright):
        p.setPen(Qt.NoPen)
        g = QRadialGradient(cx, cy, R * 0.8)
        a = int((20 + 38 * inten) * bright)
        g.setColorAt(0.0, QColor(C_R, C_G, C_B, a))
        g.setColorAt(0.55, QColor(C_R, C_G, C_B, int(a * 0.4)))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(g)
        p.drawEllipse(QPointF(cx, cy), R * 0.8, R * 0.78)
        g2 = QRadialGradient(cx, cy, R * 0.16)
        g2.setColorAt(0.0, QColor(225, 230, 236, int((55 + 55 * inten) * bright)))
        g2.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(g2)
        p.drawEllipse(QPointF(cx, cy), R * 0.16, R * 0.16)

    def _caption_text(self, p, cx, cy, maxw):
        if not self._caption:
            return
        f = QFont("Segoe UI"); f.setPixelSize(max(12, int(self.width() * 0.014)))
        p.setFont(f); p.setPen(QColor(150, 155, 163))
        rect = QRectF(cx - maxw / 2, cy - 14, maxw, 30)
        p.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, self._caption)
