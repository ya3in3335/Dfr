"""The Dexter orb — a modern monochrome (black & gray) animated sphere.

Drawn entirely with QPainter:
* concentric gray rings + a rotating dashed ring (modern HUD feel),
* a near-black core with a layered-sine waveform and caption,
* an **invoke animation**: expanding ring bursts fired via ``pulse()`` whenever
  Dexter is activated,
* **audio reactivity**: ``set_level()`` drives the waveform amplitude and a
  subtle scale so the orb visibly responds to the microphone / voice.
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
    "speaking": "",
}
TARGET = {"idle": 0.16, "listening": 0.6, "thinking": 0.45, "speaking": 0.9}

WHITE = QColor(232, 234, 237)
GRAY = QColor(120, 124, 132)
GRAY_DIM = QColor(70, 72, 78)


class OrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self._phase = 0.0
        self._intensity = 0.16
        self._target = 0.16
        self._level = 0.0          # smoothed audio level (0..1)
        self._state = "idle"
        self._caption = CAPTIONS["idle"]
        self._spin = 0.0
        self._pulses: list[float] = []   # start-times of invoke bursts
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    # -- public API ----------------------------------------------------------
    def set_state(self, state: str):
        self._state = state
        self._target = TARGET.get(state, 0.16)
        if state != "speaking":
            self._caption = CAPTIONS.get(state, self._caption)
        self.update()

    def set_caption(self, text: str):
        self._caption = text
        self.update()

    def set_level(self, level: float):
        """Live audio level (0..1) from the mic or voice output."""
        self._level = max(self._level * 0.6, min(1.0, level))  # fast attack

    def pulse(self):
        """Fire an invoke animation (expanding ring burst)."""
        self._pulses.append(time.monotonic())
        self._target = max(self._target, 0.85)

    # -- animation -----------------------------------------------------------
    def _tick(self):
        reactive = max(self._target, self._level)
        self._intensity += (reactive - self._intensity) * 0.14
        self._level *= 0.90
        self._phase += 0.03 + self._intensity * 0.14
        self._spin += 0.5
        now = time.monotonic()
        self._pulses = [t for t in self._pulses if now - t < 1.1]
        self.update()

    # -- painting ------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base = min(w, h) / 2 * 0.92
        R = base * (1.0 + 0.03 * self._intensity)   # subtle scale with intensity

        # soft outer glow (white, low alpha)
        glow = QRadialGradient(cx, cy, R * 1.2)
        a = int(40 + 70 * self._intensity)
        glow.setColorAt(0.0, QColor(255, 255, 255, a))
        glow.setColorAt(0.5, QColor(160, 164, 172, int(a * 0.4)))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen); p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), R * 1.18, R * 1.18)

        # invoke pulses — expanding fading rings
        for t in self._pulses:
            prog = (time.monotonic() - t) / 1.1
            if prog < 0 or prog > 1:
                continue
            rr = R * (0.6 + prog * 0.6)
            alpha = int(180 * (1 - prog))
            pen = QPen(QColor(255, 255, 255, alpha)); pen.setWidthF(2.0)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), rr, rr)

        # rings (grayscale)
        self._ring(p, cx, cy, R * 0.86, R * 0.012, GRAY_DIM)
        self._dashed_ring(p, cx, cy, R * 0.80, R * 0.006, self._spin)
        self._ring(p, cx, cy, R * 0.68, R * 0.018, GRAY)
        self._ring(p, cx, cy, R * 0.60, 1.6, WHITE, glow=True)

        # rotating highlight arc
        self._arc(p, cx, cy, R * 0.68, R * 0.018, self._spin * 1.2,
                  QColor(255, 255, 255, 180), span=55)

        # dark core
        coreR = R * 0.56
        core = QRadialGradient(cx, cy - coreR * 0.1, coreR)
        core.setColorAt(0.0, QColor(46, 48, 54, 220))
        core.setColorAt(0.55, QColor(18, 18, 21, 240))
        core.setColorAt(1.0, QColor(8, 8, 10, 255))
        p.setBrush(core); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), coreR, coreR)

        # waveform + caption inside the core
        p.save()
        p.setClipPath(self._circle(cx, cy, coreR * 0.98))
        self._waveform(p, cx, cy - coreR * 0.12, coreR * 1.5, coreR * 0.5)
        p.restore()
        self._caption_text(p, cx, cy + coreR * 0.42, coreR * 1.5)
        p.end()

    def _circle(self, cx, cy, r):
        path = QPainterPath(); path.addEllipse(QPointF(cx, cy), r, r); return path

    def _ring(self, p, cx, cy, radius, width, color: QColor, glow=False):
        if glow:
            pen = QPen(QColor(color.red(), color.green(), color.blue(), 60))
            pen.setWidthF(width * 3.2); p.setPen(pen); p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), radius, radius)
        pen = QPen(color); pen.setWidthF(width)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), radius, radius)

    def _dashed_ring(self, p, cx, cy, radius, width, angle):
        pen = QPen(QColor(150, 154, 162, 150)); pen.setWidthF(max(1.0, width))
        pen.setDashPattern([1, 5]); pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.save(); p.translate(cx, cy); p.rotate(angle * 0.3)
        p.drawEllipse(QPointF(0, 0), radius, radius); p.restore()

    def _arc(self, p, cx, cy, radius, width, angle, color, span=55):
        pen = QPen(color); pen.setWidthF(width); pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        p.drawArc(rect, int(-angle * 16), int(span * 16))

    def _waveform(self, p, cx, cy, width, height):
        lines = 9
        half = width / 2
        for l in range(lines):
            lp = l / (lines - 1) - 0.5
            amp = height * self._intensity * (1 - abs(lp) * 0.5)
            alpha = 0.12 + 0.20 * (1 - abs(lp) * 1.3)
            pen = QPen(QColor(232, 234, 237, int(255 * max(0.05, alpha))))
            pen.setWidthF(1.1); p.setPen(pen)
            path = QPainterPath(); steps = 90
            for s in range(steps + 1):
                t = s / steps
                x = cx - half + t * width
                env = math.exp(-((t - 0.5) * 3.2) ** 2)
                y = cy + (math.sin(t * 15 + self._phase + lp * 2.4) * amp * env
                          + math.sin(t * 7 - self._phase * 0.6) * amp * env * 0.35)
                path.moveTo(x, y) if s == 0 else path.lineTo(x, y)
            p.drawPath(path)
        node = QRadialGradient(cx, cy, width * 0.12)
        node.setColorAt(0.0, QColor(255, 255, 255, int(150 * (0.4 + self._intensity))))
        node.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(node); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), width * 0.12, width * 0.12)

    def _caption_text(self, p, cx, cy, maxw):
        if not self._caption:
            return
        f = QFont("Segoe UI"); f.setPixelSize(max(12, int(self.width() * 0.015)))
        p.setFont(f); p.setPen(QColor(210, 213, 218))
        rect = QRectF(cx - maxw / 2, cy - 18, maxw, 44)
        p.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter | Qt.TextWordWrap, self._caption)
