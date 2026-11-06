"""The Dexter orb — a photoreal grayscale glass sphere drawn with QPainter.

Rendering pipeline (back → front) mimics how light behaves in a real glass bead:
  halo → body volume + vertical shading → refractive caustic (bottom) → liquid
  ripples → inner total-internal-reflection crescent → top ambient shadow →
  Fresnel rim → specular reflections (soft key, sharp hotspot, faint fill).

Everything is procedural (no textures). The liquid ripples drift continuously —
subtle when idle, stronger when listening/speaking — and the caustic brightens
with voice level, so the sphere always undulates and reacts.
"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (QColor, QLinearGradient, QPainter, QPen, QRadialGradient,
                           QPainterPath, QFont)
from PySide6.QtWidgets import QWidget

CAPTIONS = {
    "idle": "Hi, how can I help you …",
    "listening": "Listening …",
    "thinking": "Processing …",
    "speaking": "Speaking …",
}
TARGET = {"idle": 0.28, "listening": 0.75, "thinking": 0.55, "speaking": 0.95}


class OrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self._phase = 0.0
        self._intensity = 0.28
        self._target = 0.28
        self._level = 0.0
        self._state = "idle"
        self._caption = CAPTIONS["idle"]
        self._pulses: list[float] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    # -- public API ----------------------------------------------------------
    def set_state(self, state: str):
        self._state = state
        self._target = TARGET.get(state, 0.28)
        self._caption = CAPTIONS.get(state, self._caption)
        self.update()

    def set_caption(self, text: str):
        self._caption = text
        self.update()

    def set_level(self, level: float):
        self._level = max(self._level * 0.6, min(1.0, level))

    def pulse(self):
        self._pulses.append(time.monotonic())
        self._target = max(self._target, 0.9)

    # -- animation -----------------------------------------------------------
    def _tick(self):
        reactive = max(self._target, self._level)
        self._intensity += (reactive - self._intensity) * 0.12
        self._level *= 0.9
        self._phase += 0.02 + self._intensity * 0.10
        now = time.monotonic()
        self._pulses = [t for t in self._pulses if now - t < 1.2]
        self.update()

    # -- painting ------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - h * 0.02
        Rs = min(w, h) / 2 * 0.80

        self._halo(p, cx, cy, Rs)
        self._pulse_rings(p, cx, cy, Rs)

        sphere = QPainterPath()
        sphere.addEllipse(QPointF(cx, cy), Rs, Rs)

        self._body(p, cx, cy, Rs, sphere)
        self._vertical_shade(p, cx, cy, Rs, sphere)
        self._caustic(p, cx, cy, Rs, sphere)
        self._ripples(p, cx, cy, Rs, sphere)
        self._inner_crescent(p, cx, cy, Rs, sphere)
        self._top_shadow(p, cx, cy, Rs, sphere)
        self._fresnel_rim(p, cx, cy, Rs)
        self._speculars(p, cx, cy, Rs, sphere)

        self._caption_text(p, cx, cy + Rs + min(w, h) * 0.035, Rs * 2)
        p.end()

    # ---- individual layers -------------------------------------------------
    def _halo(self, p, cx, cy, Rs):
        g = QRadialGradient(cx, cy, Rs * 1.4)
        a = int(26 + 55 * self._intensity)
        g.setColorAt(0.62, QColor(188, 196, 208, a))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen); p.setBrush(g)
        p.drawEllipse(QPointF(cx, cy), Rs * 1.36, Rs * 1.36)

    def _pulse_rings(self, p, cx, cy, Rs):
        now = time.monotonic()
        for t in self._pulses:
            prog = (now - t) / 1.2
            if 0 <= prog <= 1:
                rr = Rs * (1.0 + prog * 0.45)
                pen = QPen(QColor(235, 238, 242, int(140 * (1 - prog))))
                pen.setWidthF(1.8); p.setPen(pen); p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(cx, cy), rr, rr)

    def _body(self, p, cx, cy, Rs, sphere):
        # clear water-drop body: mostly transparent (you see the black through
        # it), gently lit upper-left, darkening to a thin dense edge
        g = QRadialGradient(cx - Rs * 0.26, cy - Rs * 0.30, Rs * 1.5)
        g.setColorAt(0.0, QColor(150, 156, 165, 120))
        g.setColorAt(0.42, QColor(70, 74, 82, 110))
        g.setColorAt(0.72, QColor(34, 36, 42, 140))
        g.setColorAt(0.93, QColor(20, 21, 26, 195))
        g.setColorAt(1.0, QColor(10, 11, 14, 235))
        p.setPen(Qt.NoPen); p.setBrush(g)
        p.drawPath(sphere)

    def _vertical_shade(self, p, cx, cy, Rs, sphere):
        # darker top, lighter bottom (transmitted light) — subtle
        p.save(); p.setClipPath(sphere)
        g = QLinearGradient(cx, cy - Rs, cx, cy + Rs)
        g.setColorAt(0.0, QColor(8, 9, 12, 95))
        g.setColorAt(0.5, QColor(0, 0, 0, 0))
        g.setColorAt(1.0, QColor(235, 238, 243, int(55 + 55 * self._intensity)))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(sphere)
        p.restore()

    def _caustic(self, p, cx, cy, Rs, sphere):
        # focused bright spot where light converges through the glass (bottom)
        p.save(); p.setClipPath(sphere)
        k = 0.55 + 0.45 * self._intensity
        g = QRadialGradient(cx + Rs * 0.04, cy + Rs * 0.44, Rs * 0.62)
        g.setColorAt(0.0, QColor(252, 253, 255, int(245 * k)))
        g.setColorAt(0.22, QColor(214, 219, 227, int(150 * k)))
        g.setColorAt(0.6, QColor(120, 125, 133, 0))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(sphere)
        p.restore()

    def _ripples(self, p, cx, cy, Rs, sphere):
        p.save(); p.setClipPath(sphere)
        lines = 5
        drift = math.sin(self._phase * 0.5) * Rs * 0.03
        for i in range(lines):
            fy = 0.02 + (i / (lines - 1)) * 0.52
            yc = cy + fy * Rs + drift
            fade = 1 - max(0.0, fy) * 0.5
            amp = Rs * (0.025 + 0.055 * self._intensity) * fade
            alpha = int(255 * (0.018 + 0.035 * fade))
            pen = QPen(QColor(232, 236, 242, max(5, alpha)))
            pen.setWidthF(1.3); pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
            path = QPainterPath(); steps = 90
            for s in range(steps + 1):
                t = s / steps
                x = cx - Rs + t * 2 * Rs
                env = math.sin(math.pi * t) ** 1.3
                y = yc + math.sin(t * 7 + self._phase + fy * 2.2) * amp * env \
                       + math.sin(t * 3.3 - self._phase * 0.6) * amp * 0.45 * env
                path.moveTo(x, y) if s == 0 else path.lineTo(x, y)
            p.drawPath(path)
        p.restore()

    def _inner_crescent(self, p, cx, cy, Rs, sphere):
        # total internal reflection — a bright crescent hugging the lower rim
        p.save(); p.setClipPath(sphere)
        g = QRadialGradient(cx, cy - Rs * 0.48, Rs * 1.6)
        g.setColorAt(0.0, QColor(255, 255, 255, 0))
        g.setColorAt(0.86, QColor(235, 239, 244, 0))
        g.setColorAt(0.93, QColor(236, 240, 245, 150))
        g.setColorAt(0.985, QColor(252, 253, 255, 215))
        g.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(sphere)
        p.restore()

    def _top_shadow(self, p, cx, cy, Rs, sphere):
        # faint ambient darkening of the upper interior for depth
        p.save(); p.setClipPath(sphere)
        g = QRadialGradient(cx, cy - Rs * 0.62, Rs * 0.95)
        g.setColorAt(0.0, QColor(6, 7, 10, 120))
        g.setColorAt(0.7, QColor(6, 7, 10, 0))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(sphere)
        p.restore()

    def _fresnel_rim(self, p, cx, cy, Rs):
        # thin very bright edge, strongest top & bottom (Fresnel)
        g = QRadialGradient(cx, cy, Rs)
        g.setColorAt(0.0, QColor(255, 255, 255, 0))
        g.setColorAt(0.9, QColor(210, 215, 223, 0))
        g.setColorAt(0.955, QColor(224, 229, 236, 90))
        g.setColorAt(0.99, QColor(250, 252, 255, 210))
        g.setColorAt(1.0, QColor(255, 255, 255, 30))
        p.setPen(Qt.NoPen); p.setBrush(g)
        p.drawEllipse(QPointF(cx, cy), Rs, Rs)

    def _speculars(self, p, cx, cy, Rs, sphere):
        p.save(); p.setClipPath(sphere)
        # soft key reflection (studio softbox), upper area
        self._blob(p, cx - Rs * 0.20, cy - Rs * 0.50, Rs * 0.58, Rs * 0.30, -16, 150)
        # faint, very diffuse environment fill, upper right
        self._blob(p, cx + Rs * 0.38, cy - Rs * 0.28, Rs * 0.30, Rs * 0.52, 26, 38)
        # crisp hotspot
        self._blob(p, cx - Rs * 0.30, cy - Rs * 0.44, Rs * 0.085, Rs * 0.06, 0, 255)
        p.restore()

    def _blob(self, p, x, y, rx, ry, rot, alpha):
        p.save(); p.translate(x, y); p.rotate(rot)
        g = QRadialGradient(0, 0, max(rx, ry))
        g.setColorAt(0.0, QColor(255, 255, 255, alpha))
        g.setColorAt(0.5, QColor(246, 248, 251, int(alpha * 0.38)))
        g.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen); p.setBrush(g)
        p.scale(1.0, ry / rx if rx else 1.0)
        p.drawEllipse(QPointF(0, 0), rx, rx)
        p.restore()

    def _caption_text(self, p, cx, cy, maxw):
        if not self._caption:
            return
        f = QFont("Segoe UI"); f.setPixelSize(max(12, int(self.width() * 0.014)))
        p.setFont(f); p.setPen(QColor(150, 155, 163))
        rect = QRectF(cx - maxw / 2, cy - 14, maxw, 30)
        p.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, self._caption)
