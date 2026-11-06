"""The Dexter orb — a turbulent particle ring rendered with QPainter.

Hundreds of small glowing points form a ring whose radius is displaced by
travelling waves + per-particle turbulence, so the ring churns organically.
It rotates slowly and undulates gently when idle, and churns much harder when
listening / speaking (audio reactive). Drawn additively on black for a bloom
glow — no textures.

Public API: ``set_state``, ``set_caption``, ``set_level``, ``pulse``.
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
TARGET = {"idle": 0.22, "listening": 0.8, "thinking": 0.55, "speaking": 0.95}

# Particle glow color (cool teal, like the reference). Tweak here to recolor.
C_R, C_G, C_B = 120, 224, 232

LAYERS = 6
PER_LAYER = 92


class OrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self._phase = 0.0
        self._intensity = 0.22
        self._target = 0.22
        self._level = 0.0
        self._state = "idle"
        self._caption = CAPTIONS["idle"]
        self._pulses: list[float] = []
        self._particles = self._build_particles()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _build_particles(self):
        rnd = random.Random(7)
        parts = []
        for l in range(LAYERS):
            for i in range(PER_LAYER):
                a0 = (i / PER_LAYER) * 2 * math.pi + rnd.uniform(-0.03, 0.03)
                parts.append({
                    "l": l,
                    "a": a0,
                    "ph": rnd.uniform(0, 2 * math.pi),
                    "jit": rnd.uniform(-1, 1),
                    "spray": rnd.random() < 0.14,
                    "sz": rnd.uniform(1.0, 2.1),
                    "b": rnd.uniform(0.45, 1.0),
                    "sp": rnd.uniform(0.8, 1.4),   # per-particle wave speed
                })
        return parts

    # -- public API ----------------------------------------------------------
    def set_state(self, state: str):
        self._state = state
        self._target = TARGET.get(state, 0.22)
        self._caption = CAPTIONS.get(state, self._caption)
        self.update()

    def set_caption(self, text: str):
        self._caption = text
        self.update()

    def set_level(self, level: float):
        self._level = max(self._level * 0.6, min(1.0, level))

    def pulse(self):
        self._pulses.append(time.monotonic())
        self._target = max(self._target, 0.95)

    # -- animation -----------------------------------------------------------
    def _tick(self):
        reactive = max(self._target, self._level)
        self._intensity += (reactive - self._intensity) * 0.10
        self._level *= 0.9
        self._phase += 0.016 + self._intensity * 0.06
        now = time.monotonic()
        self._pulses = [t for t in self._pulses if now - t < 1.2]
        self.update()

    def _pulse_amp(self) -> float:
        now = time.monotonic()
        amp = 0.0
        for t in self._pulses:
            prog = (now - t) / 1.2
            if 0 <= prog <= 1:
                amp = max(amp, math.sin(prog * math.pi))
        return amp

    # -- painting ------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - h * 0.02
        R = min(w, h) / 2 * 0.72
        t = self._phase
        inten = self._intensity + 0.45 * self._pulse_amp()
        rot = t * 0.12
        squash = 0.96

        self._core(p, cx, cy, R, inten)

        p.setCompositionMode(QPainter.CompositionMode_Plus)
        p.setPen(Qt.NoPen)
        ic = min(1.0, inten)
        base_amp = R * (0.03 + 0.095 * ic)          # keep a defined ring band
        for pt in self._particles:
            l = pt["l"]
            Rl = R * (0.85 + 0.032 * l)             # tight concentric band
            a = pt["a"] + rot + l * 0.04
            k1, k2, k3 = 3 + l, 6 - (l % 3), 9
            disp = (math.sin(k1 * a + t * pt["sp"] + pt["ph"])
                    + 0.55 * math.sin(k2 * a - t * 1.1)
                    + 0.35 * math.sin(k3 * a + t * 0.6 + pt["ph"]))
            amp = base_amp * (1.5 if pt["spray"] else 1.0)
            rr = Rl + disp * amp + pt["jit"] * R * 0.015
            x = cx + rr * math.cos(a)
            y = cy + rr * math.sin(a) * squash

            peak = 0.5 + 0.5 * (disp / 1.9)            # outward = brighter
            bright = max(0.0, min(1.0, pt["b"] * (0.4 + 0.7 * peak)))
            alpha = int(55 + 165 * bright)
            p.setBrush(QColor(C_R, C_G, C_B, alpha))
            s = pt["sz"] * (1.0 + 0.45 * bright)
            p.drawEllipse(QPointF(x, y), s, s)
            if bright > 0.82:                          # hottest points sparkle
                p.setBrush(QColor(225, 252, 254, 175))
                p.drawEllipse(QPointF(x, y), s * 0.5, s * 0.5)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        self._caption_text(p, cx, cy + R + min(w, h) * 0.06, R * 2)
        p.end()

    def _core(self, p, cx, cy, R, inten):
        # faint inner disc + soft central glow
        p.setPen(Qt.NoPen)
        g = QRadialGradient(cx, cy, R * 0.75)
        a = int(22 + 40 * inten)
        g.setColorAt(0.0, QColor(C_R, C_G, C_B, a))
        g.setColorAt(0.55, QColor(C_R, C_G, C_B, int(a * 0.4)))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(g)
        p.drawEllipse(QPointF(cx, cy), R * 0.75, R * 0.72)
        # tiny faint core nucleus
        g2 = QRadialGradient(cx, cy, R * 0.16)
        g2.setColorAt(0.0, QColor(180, 240, 245, int(60 + 60 * inten)))
        g2.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(g2)
        p.drawEllipse(QPointF(cx, cy), R * 0.16, R * 0.16)

    def _caption_text(self, p, cx, cy, maxw):
        if not self._caption:
            return
        f = QFont("Segoe UI"); f.setPixelSize(max(12, int(self.width() * 0.014)))
        p.setFont(f); p.setPen(QColor(150, 175, 180))
        rect = QRectF(cx - maxw / 2, cy - 14, maxw, 30)
        p.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, self._caption)
