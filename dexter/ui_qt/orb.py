"""The Dexter orb — a glossy 3D glass sphere rendered with QPainter (grayscale).

Looks like a real translucent glass bead: volumetric spherical shading, a glowing
bottom core, a bright glass rim, and soft specular highlights. Inside, liquid
ripples drift continuously — gently when idle, stronger when listening/speaking
— so the orb always "undulates". Everything is drawn graphically (no images).

Public API: ``set_state``, ``set_caption``, ``set_level`` (audio reactive),
``pulse`` (invoke burst).
"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient, QPainterPath, QFont
from PySide6.QtWidgets import QWidget

CAPTIONS = {
    "idle": "Hi, how can I help you …",
    "listening": "Listening …",
    "thinking": "Processing …",
    "speaking": "Speaking …",
}
# idle is intentionally non-zero so the glass keeps rippling even when silent.
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
        if state != "speaking":
            self._caption = CAPTIONS.get(state, self._caption)
        else:
            self._caption = CAPTIONS["speaking"]
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
        self._bottom_glow(p, cx, cy, Rs, sphere)
        self._ripples(p, cx, cy, Rs, sphere)
        self._rim(p, cx, cy, Rs)
        self._speculars(p, cx, cy, Rs, sphere)

        self._caption_text(p, cx, cy + Rs + min(w, h) * 0.035, Rs * 2)
        p.end()

    def _halo(self, p, cx, cy, Rs):
        g = QRadialGradient(cx, cy, Rs * 1.35)
        a = int(28 + 55 * self._intensity)
        g.setColorAt(0.6, QColor(190, 196, 206, a))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen); p.setBrush(g)
        p.drawEllipse(QPointF(cx, cy), Rs * 1.32, Rs * 1.32)

    def _pulse_rings(self, p, cx, cy, Rs):
        now = time.monotonic()
        for t in self._pulses:
            prog = (now - t) / 1.2
            if 0 <= prog <= 1:
                rr = Rs * (1.0 + prog * 0.45)
                pen = QPen(QColor(235, 238, 242, int(150 * (1 - prog))))
                pen.setWidthF(2.0)
                p.setPen(pen); p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(cx, cy), rr, rr)

    def _body(self, p, cx, cy, Rs, sphere):
        # volumetric sphere shading — translucent, darker at the top/edges
        g = QRadialGradient(cx, cy - Rs * 0.22, Rs * 1.18)
        g.setColorAt(0.0, QColor(150, 155, 163, 180))
        g.setColorAt(0.55, QColor(92, 96, 104, 175))
        g.setColorAt(0.85, QColor(42, 44, 50, 205))
        g.setColorAt(1.0, QColor(16, 17, 20, 235))
        p.setPen(Qt.NoPen); p.setBrush(g)
        p.drawPath(sphere)

    def _bottom_glow(self, p, cx, cy, Rs, sphere):
        # the glowing light core near the bottom (brightens with intensity)
        p.save(); p.setClipPath(sphere)
        k = 0.45 + 0.55 * self._intensity
        g = QRadialGradient(cx, cy + Rs * 0.42, Rs * 1.05)
        g.setColorAt(0.0, QColor(235, 238, 243, int(210 * k)))
        g.setColorAt(0.35, QColor(170, 175, 183, int(110 * k)))
        g.setColorAt(0.8, QColor(90, 94, 102, 0))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen); p.setBrush(g)
        p.drawPath(sphere)
        p.restore()

    def _ripples(self, p, cx, cy, Rs, sphere):
        # soft liquid waves drifting through the lower half of the glass
        p.save(); p.setClipPath(sphere)
        lines = 7
        drift = math.sin(self._phase * 0.5) * Rs * 0.04   # whole body sloshes
        for i in range(lines):
            fy = -0.12 + (i / (lines - 1)) * 0.62          # biased to lower half
            yc = cy + fy * Rs + drift
            fade = 1 - max(0.0, fy) * 0.5
            amp = Rs * (0.045 + 0.075 * self._intensity) * fade
            alpha = int(255 * (0.035 + 0.055 * fade))
            pen = QPen(QColor(228, 232, 238, max(8, alpha)))
            pen.setWidthF(1.6); pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
            path = QPainterPath(); steps = 90
            for s in range(steps + 1):
                t = s / steps
                x = cx - Rs + t * 2 * Rs
                env = math.sin(math.pi * t) ** 1.3         # fade at the sides
                y = yc + math.sin(t * 7 + self._phase + fy * 2.2) * amp * env \
                       + math.sin(t * 3.3 - self._phase * 0.6) * amp * 0.45 * env
                path.moveTo(x, y) if s == 0 else path.lineTo(x, y)
            p.drawPath(path)
        p.restore()

    def _rim(self, p, cx, cy, Rs):
        # bright glass rim around the circumference
        g = QRadialGradient(cx, cy, Rs)
        g.setColorAt(0.0, QColor(255, 255, 255, 0))
        g.setColorAt(0.82, QColor(200, 205, 212, 0))
        g.setColorAt(0.9, QColor(210, 215, 222, 70))
        g.setColorAt(0.965, QColor(240, 243, 247, 180))
        g.setColorAt(1.0, QColor(255, 255, 255, 25))
        p.setPen(Qt.NoPen); p.setBrush(g)
        p.drawEllipse(QPointF(cx, cy), Rs, Rs)

    def _speculars(self, p, cx, cy, Rs, sphere):
        p.save(); p.setClipPath(sphere)
        # large soft highlight, upper area
        self._blob(p, cx - Rs * 0.18, cy - Rs * 0.52, Rs * 0.62, Rs * 0.34, -18, 185)
        # secondary highlight, upper right
        self._blob(p, cx + Rs * 0.34, cy - Rs * 0.34, Rs * 0.26, Rs * 0.5, 28, 120)
        # tiny crisp hotspot
        self._blob(p, cx - Rs * 0.28, cy - Rs * 0.44, Rs * 0.12, Rs * 0.09, 0, 230)
        p.restore()

    def _blob(self, p, x, y, rx, ry, rot, alpha):
        p.save(); p.translate(x, y); p.rotate(rot)
        g = QRadialGradient(0, 0, max(rx, ry))
        g.setColorAt(0.0, QColor(255, 255, 255, alpha))
        g.setColorAt(0.5, QColor(245, 247, 250, int(alpha * 0.4)))
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
