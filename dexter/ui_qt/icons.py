"""Crisp SVG icons rendered to themeable pixmaps/icons for the Qt UI.

Each icon is a small inline SVG using ``currentColor`` for its strokes. The
helpers recolor and rasterise them at any size with the device pixel ratio, so
they stay sharp on HiDPI screens.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

# 24x24 viewBox, stroke-based line icons.
_SVG = {
    "mic": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2" width="6" height="12" rx="3"/>
        <path d="M5 11a7 7 0 0 0 14 0"/><line x1="12" y1="18" x2="12" y2="22"/>
        <line x1="8" y1="22" x2="16" y2="22"/></svg>""",
    "send": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/>
        <path d="M22 2 15 22l-4-9-9-4 20-7z"/></svg>""",
    "settings": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
        stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33
        1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83
        l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82
        l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51
        1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09
        a1.65 1.65 0 0 0-1.51 1z"/></svg>""",
    "headphones": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"><path d="M3 14v-2a9 9 0 0 1 18 0v2"/>
        <path d="M21 16a2 2 0 0 1-2 2h-1v-6h1a2 2 0 0 1 2 2z"/>
        <path d="M3 16a2 2 0 0 0 2 2h1v-6H5a2 2 0 0 0-2 2z"/></svg>""",
    "close": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
        stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>""",
    "key": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"><circle cx="7.5" cy="15.5" r="4.5"/>
        <path d="M10.5 12.5 20 3"/><path d="m16 7 3 3"/><path d="m18 5 2 2"/></svg>""",
    "eye": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/>
        <circle cx="12" cy="12" r="3"/></svg>""",
    "cpu": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
        stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="14" height="14" rx="2"/>
        <rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></svg>""",
    "tasks": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"><path d="m3 7 2 2 4-4"/><path d="m3 17 2 2 4-4"/>
        <line x1="13" y1="6" x2="21" y2="6"/><line x1="13" y1="18" x2="21" y2="18"/></svg>""",
    "shield": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
        stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <path d="m9 12 2 2 4-4"/></svg>""",
    "trash": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4h8v2"/>
        <path d="M19 6l-1 14H6L5 6"/></svg>""",
    "power": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"><path d="M18.4 6.6a9 9 0 1 1-12.8 0"/>
        <line x1="12" y1="2" x2="12" y2="12"/></svg>""",
}


def _render(name: str, size: int, color: str, dpr: float = 1.0) -> QPixmap:
    svg = _SVG.get(name, "").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    px = max(1, int(size * dpr))
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(p)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def pixmap(name: str, size: int = 22, color: str = "#dfeefc", dpr: float = 2.0) -> QPixmap:
    return _render(name, size, color, dpr)


def icon(name: str, size: int = 22, color: str = "#dfeefc") -> QIcon:
    return QIcon(_render(name, size, color, 2.0))
