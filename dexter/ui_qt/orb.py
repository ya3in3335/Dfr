"""The animated Dexter orb, drawn entirely with QPainter.

Concentric glowing rings (blue torus, blue ring, crisp cyan ring) around a dark
core that holds a layered-sine waveform and a caption. The waveform intensity
eases toward a target set by the current state (idle/listening/thinking/speaking)
or driven live by audio level during speech.
"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (QColor, QPainter, QPen, QRadialGradient, QPainterPath,
                           QFont)
from PySide6.QtWidgets import QWidget

CAPTIONS = {
    "idle": "Hi, how can I help you …",
    "listening": "Listening …",
    "thinking": "Processing …",
    "speaking": "",
}
TARGET = {"idle": 0.18, "listening": 0.7, "thinking": 0.5, "speaking": 0.95}


class OrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self._phase = 0.0
        self._intensity = 0.18
        self._target = 0.18
        self._state = "idle"
        self._caption = CAPTIONS["idle"]
        self._spin = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 fps

    # -- public API ----------------------------------------------------------
    def set_state(self, state: str):
        self._state = state
        self._target = TARGET.get(state, 0.18)
        if state != "speaking":
            self._caption = CAPTIONS.get(state, self._caption)
        self.update()

    def set_caption(self, text: str):
        self._caption = text
        self.update()

    def set_level(self, level: float):
        """Audio-reactive intensity (0..1) while speaking."""
        self._target = max(0.3, min(0.98, level))

    # -- animation -----------------------------------------------------------
    def _tick(self):
        self._intensity += (self._target - self._intensity) * 0.08
        self._phase += 0.04 + self._intensity * 0.12
        self._spin += 0.6
        self.update()

    # -- painting ------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        R = min(w, h) / 2 * 0.92

        # outer soft glow
        glow = QRadialGradient(cx, cy, R * 1.15)
        gcol = QColor(47, 123, 255)
        if self._state == "thinking":
            gcol = QColor(120, 90, 255)
        glow.setColorAt(0.0, QColor(gcol.red(), gcol.green(), gcol.blue(), 150))
        glow.setColorAt(0.45, QColor(31, 90, 200, 70))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), R * 1.12, R * 1.12)

        # rings (multiple translucent strokes approximate a glow)
        self._ring(p, cx, cy, R * 0.86, R * 0.085, QColor(47, 123, 255), 0.42)
        self._ring(p, cx, cy, R * 0.72, R * 0.040, QColor(60, 130, 255), 0.80)
        self._ring(p, cx, cy, R * 0.605, 2.2, QColor(53, 228, 255),
                   1.0 if self._state != "listening" else 1.0, cyan=True)

        # rotating energy arcs on the rings
        self._arc(p, cx, cy, R * 0.86, R * 0.085, self._spin, QColor(190, 245, 255, 150))
        self._arc(p, cx, cy, R * 0.72, R * 0.040, -self._spin * 1.3, QColor(190, 245, 255, 130))

        # dark core
        coreR = R * 0.56
        core = QRadialGradient(cx, cy - coreR * 0.1, coreR)
        core.setColorAt(0.0, QColor(40, 120, 235, 150))
        core.setColorAt(0.42, QColor(10, 28, 50, 190))
        core.setColorAt(1.0, QColor(5, 12, 22, 250))
        p.setBrush(core)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), coreR, coreR)

        # waveform + caption inside the core
        p.save()
        p.setClipPath(self._circle_path(cx, cy, coreR * 0.98))
        self._waveform(p, cx, cy - coreR * 0.12, coreR * 1.5, coreR * 0.5)
        p.restore()
        self._draw_caption(p, cx, cy + coreR * 0.42, coreR * 1.5)
        p.end()

    def _circle_path(self, cx, cy, r):
        path = QPainterPath()
        path.addEllipse(QPointF(cx, cy), r, r)
        return path

    def _ring(self, p, cx, cy, radius, width, color, alpha, cyan=False):
        for i, a in enumerate((alpha * 0.4, alpha)):
            pen = QPen(QColor(color.red(), color.green(), color.blue(), int(255 * a)))
            pen.setWidthF(width * (1.8 if i == 0 else 1.0))
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), radius, radius)

    def _arc(self, p, cx, cy, radius, width, angle, color):
        pen = QPen(color)
        pen.setWidthF(width)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        p.drawArc(rect, int(angle * 16), int(70 * 16))

    def _waveform(self, p, cx, cy, width, height):
        lines = 9
        half = width / 2
        for l in range(lines):
            lp = l / (lines - 1) - 0.5
            amp = height * self._intensity * (1 - abs(lp) * 0.5)
            alpha = 0.10 + 0.16 * (1 - abs(lp) * 1.3)
            pen = QPen(QColor(90, 220, 255, int(255 * max(0.05, alpha))))
            pen.setWidthF(1.1)
            p.setPen(pen)
            path = QPainterPath()
            steps = 90
            for s in range(steps + 1):
                t = s / steps
                x = cx - half + t * width
                env = math.exp(-((t - 0.5) * 3.2) ** 2)
                y = cy + (math.sin(t * 15 + self._phase + lp * 2.4) * amp * env
                          + math.sin(t * 7 - self._phase * 0.6) * amp * env * 0.35)
                if s == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            p.drawPath(path)
        # central bright node
        node = QRadialGradient(cx, cy, width * 0.12)
        node.setColorAt(0.0, QColor(180, 245, 255, int(150 * (0.4 + self._intensity))))
        node.setColorAt(1.0, QColor(180, 245, 255, 0))
        p.setBrush(node)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), width * 0.12, width * 0.12)

    def _draw_caption(self, p, cx, cy, maxw):
        if not self._caption:
            return
        f = QFont("Segoe UI")
        f.setPixelSize(max(12, int(self.width() * 0.016)))
        p.setFont(f)
        p.setPen(QColor(234, 246, 255))
        rect = QRectF(cx - maxw / 2, cy - 18, maxw, 44)
        p.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter | Qt.TextWordWrap, self._caption)
