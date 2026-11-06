"""Animated splash screen shown at launch.

A strong graphic intro: a ring of particles rushes inward and orbits, the
Dexter Cyber logo fades and scales in with an overshoot, a light shimmer sweeps
across it, then the whole thing fades out and the app opens. Drawn with
QPainter; emits ``finished`` when done.
"""
from __future__ import annotations

import math
import random
import time

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget

from ..config import resource_path

DURATION = 2.6     # seconds of animation before fade
FADE = 0.55        # fade-out seconds


class SplashScreen(QWidget):
    finished = Signal()

    def __init__(self, size: int = 560):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedSize(size, size)
        self._size = size
        logo = resource_path("assets/logo_glow.png")
        if not logo.exists():
            logo = resource_path("assets/logo_full.png")
        self._logo = QPixmap(str(logo))
        self._t0 = time.monotonic()
        self._done = False
        rnd = random.Random(5)
        self._pts = [{
            "a": rnd.uniform(0, 2 * math.pi),
            "r0": rnd.uniform(1.15, 1.9),
            "sp": rnd.uniform(0.6, 1.4),
            "sz": rnd.uniform(0.8, 2.0),
            "ph": rnd.uniform(0, 6.28),
        } for _ in range(360)]
        self._center_on_screen()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _center_on_screen(self):
        screen = self.screen() or (self.windowHandle().screen() if self.windowHandle() else None)
        try:
            geo = (screen or self.screen()).availableGeometry()
            self.move(geo.center().x() - self._size // 2, geo.center().y() - self._size // 2)
        except Exception:
            pass

    def _tick(self):
        t = time.monotonic() - self._t0
        if t > DURATION:
            op = max(0.0, 1.0 - (t - DURATION) / FADE)
            self.setWindowOpacity(op)
            if op <= 0.01 and not self._done:
                self._done = True
                self._timer.stop()
                self.finished.emit()
                self.close()
                return
        self.update()

    @staticmethod
    def _ease_out(x):
        return 1 - (1 - x) ** 3

    @staticmethod
    def _ease_out_back(x):
        c1, c3 = 1.70158, 2.70158
        return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w = h = self._size
        cx, cy = w / 2, h / 2
        t = time.monotonic() - self._t0
        p.fillRect(self.rect(), QColor(6, 6, 8))

        Rring = w * 0.32
        # 1) particles rush inward and orbit
        conv = self._ease_out(min(1.0, t / 1.0))
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        p.setPen(Qt.NoPen)
        for pt in self._pts:
            r = Rring * (pt["r0"] - (pt["r0"] - 1.0) * conv)
            a = pt["a"] + t * pt["sp"] * 0.5
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a)
            alpha = int(120 * conv + 40)
            p.setBrush(QColor(210, 215, 222, min(255, alpha)))
            s = pt["sz"]
            p.drawEllipse(QPointF(x, y), s, s)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # soft glow behind logo
        glow = QRadialGradient(cx, cy, w * 0.4)
        glow.setColorAt(0.0, QColor(200, 206, 214, int(60 * self._ease_out(min(1, t / 1.2)))))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(glow); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), w * 0.4, w * 0.4)

        # 2) logo fade + scale-in with overshoot
        if not self._logo.isNull():
            lp = max(0.0, min(1.0, (t - 0.5) / 0.7))
            if lp > 0:
                scale = (0.8 + 0.2 * self._ease_out_back(lp)) * (w * 0.62 / self._logo.width())
                lw = self._logo.width() * scale
                lh = self._logo.height() * scale
                p.setOpacity(self._ease_out(lp))
                target = QRectF(cx - lw / 2, cy - lh / 2, lw, lh)
                p.drawPixmap(target, self._logo, QRectF(self._logo.rect()))
                p.setOpacity(1.0)

                # 3) shimmer sweep across the logo
                if 1.1 < t < 2.0:
                    s = (t - 1.1) / 0.9
                    band = QLinearGradient(target.left() + s * lw - lw * 0.3, target.top(),
                                           target.left() + s * lw, target.bottom())
                    band.setColorAt(0.0, QColor(255, 255, 255, 0))
                    band.setColorAt(0.5, QColor(255, 255, 255, 70))
                    band.setColorAt(1.0, QColor(255, 255, 255, 0))
                    p.setClipRect(target)
                    p.fillRect(target, band)
                    p.setClipping(False)

        # thin progress arc
        if t < DURATION:
            from PySide6.QtGui import QPen
            pen = QPen(QColor(210, 215, 222, 150)); pen.setWidthF(2.2); pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            rr = w * 0.42
            span = int(360 * min(1.0, t / DURATION) * 16)
            p.drawArc(QRectF(cx - rr, cy - rr, rr * 2, rr * 2), 90 * 16, -span)
        p.end()
