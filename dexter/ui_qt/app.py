"""Dexter Cyber — PySide6 desktop application (main window)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from .. import __version__
from ..config import resource_path, settings
from ..core.assistant import Assistant
from . import icons
from .orb import OrbWidget
from .settings_dialog import SettingsDialog
from .theme import CYAN, DANGER, INK, INK_DIM, OK, QSS, WARN
from .worker import AsyncLoop, Bridge, WakeListener

ACCENT = {"cyan": CYAN, "green": OK, "amber": WARN, "red": DANGER}
TASK_COLOR = {"pending": INK_DIM, "active": CYAN, "done": OK, "failed": DANGER}


# ---------------------------------------------------------------- consent
class ConsentDialog(QDialog):
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.setWindowTitle("Dexter Cyber — Authorization")
        self.setMinimumWidth(560)
        self.setStyleSheet(QSS)
        self.checks = {}
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 20); v.setSpacing(12)
        head = QLabel("First-run authorization"); head.setObjectName("panelHead")
        v.addWidget(head)
        lead = QLabel("Dexter can operate this computer for you. Grant what you are comfortable "
                      "with — you are asked only once; it is stored locally and changeable anytime.")
        lead.setObjectName("hint"); lead.setWordWrap(True); v.addWidget(lead)
        for cap in assistant.permissions.snapshot()["capabilities"]:
            cb = QCheckBox(f"{cap['title']}  ·  {cap['risk'].upper()}\n{cap['description']}")
            cb.setChecked(True); self.checks[cap["key"]] = cb
            v.addWidget(cb)
        row = QHBoxLayout(); row.addStretch(1)
        ok = QPushButton("Authorize Dexter"); ok.setObjectName("primary")
        ok.clicked.connect(self._accept); row.addWidget(ok)
        v.addLayout(row)

    def _accept(self):
        grants = {k: cb.isChecked() for k, cb in self.checks.items()}
        self.assistant.permissions.accept(grants)
        self.accept()


# ---------------------------------------------------------------- main window
class DexterWindow(QWidget):
    def __init__(self, assistant: Assistant, loop: AsyncLoop):
        super().__init__()
        self.assistant = assistant
        self.loop = loop
        self.bridge = Bridge()
        self.bridge.event.connect(self.on_event)
        self.wake = None
        self.cards = {}
        self.tasks = {}
        self.player = None
        self._audio_out = None

        self.setObjectName("root")
        self.setWindowTitle("Dexter Cyber")
        self.resize(1160, 740)
        self.setStyleSheet(QSS)
        self._build()

    # ---- layout ----
    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # top bar
        top = QHBoxLayout(); top.setContentsMargins(18, 12, 18, 12)
        brand = QLabel('DEXTER <span id="x" style="color:#35e4ff;">CYBER</span>')
        brand.setObjectName("brand"); brand.setTextFormat(Qt.RichText)
        top.addWidget(brand)
        self.status = QLabel("offline"); self.status.setObjectName("hint")
        top.addSpacing(10); top.addWidget(self.status)
        top.addStretch(1)
        self.wake_btn = QPushButton("  Wake: off"); self.wake_btn.setObjectName("pill")
        self.wake_btn.setCheckable(True)
        self.wake_btn.setIcon(icons.icon("headphones", 18, INK))
        self.wake_btn.clicked.connect(self._toggle_wake)
        top.addWidget(self.wake_btn)
        gear = QPushButton(); gear.setObjectName("iconbtn"); gear.setFixedSize(42, 42)
        gear.setIcon(icons.icon("settings", 20, INK)); gear.setIconSize(QSize(20, 20))
        gear.clicked.connect(self._open_settings)
        top.addSpacing(8); top.addWidget(gear)
        root.addLayout(top)

        # body: orb | right panel
        body = QHBoxLayout(); body.setContentsMargins(16, 6, 16, 6); body.setSpacing(16)
        self.orb = OrbWidget()
        body.addWidget(self.orb, 3)

        right = QVBoxLayout(); right.setSpacing(10)
        right.addWidget(self._label("ACTIVITY", "tasks"))
        self.feed_area, self.feed_layout = self._scroll()
        right.addWidget(self.feed_area, 3)
        right.addWidget(self._label("TASKS", "tasks"))
        self.tasks_area, self.tasks_layout = self._scroll()
        self.tasks_area.setMaximumHeight(170)
        right.addWidget(self.tasks_area, 1)
        rw = QWidget(); rw.setLayout(right); rw.setMinimumWidth(380)
        body.addWidget(rw, 2)
        root.addLayout(body, 1)

        # composer
        comp = QHBoxLayout(); comp.setContentsMargins(18, 8, 18, 16); comp.setSpacing(8)
        self.mic = QPushButton(); self.mic.setObjectName("iconbtn"); self.mic.setFixedSize(46, 46)
        self.mic.setIcon(icons.icon("mic", 20, INK)); self.mic.setIconSize(QSize(20, 20))
        self.mic.clicked.connect(self._toggle_wake)
        self.input = QLineEdit(); self.input.setPlaceholderText("Speak or type to Dexter…")
        self.input.returnPressed.connect(self._send)
        send = QPushButton(); send.setObjectName("primary"); send.setFixedSize(46, 46)
        send.setIcon(icons.icon("send", 20, "#04121a")); send.setIconSize(QSize(20, 20))
        send.clicked.connect(self._send)
        comp.addWidget(self.mic); comp.addWidget(self.input, 1); comp.addWidget(send)
        root.addLayout(comp)

        self._refresh_status()

    def _label(self, text, ic):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(2, 0, 0, 0); l.setSpacing(6)
        pic = QLabel(); pic.setPixmap(icons.pixmap(ic, 14, CYAN)); l.addWidget(pic)
        t = QLabel(text); t.setObjectName("sectionLabel"); l.addWidget(t); l.addStretch(1)
        return w

    def _scroll(self):
        area = QScrollArea(); area.setWidgetResizable(True); area.setFrameShape(QFrame.NoShape)
        inner = QWidget(); lay = QVBoxLayout(inner); lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(8); lay.addStretch(1)
        area.setWidget(inner)
        return area, lay

    # ---- status ----
    def _refresh_status(self):
        st = self.assistant.state()
        if not st["has_api_key"]:
            self.status.setText("⚠ set OpenRouter key in Settings")
            self.orb.set_caption("Open Settings → add your OpenRouter key")
        else:
            self.status.setText(f"{st['text_model'].split('/')[-1]}  ·  voice: {st['voice_engine']}")

    # ---- actions ----
    def _send(self, text: str | None = None):
        text = (text if isinstance(text, str) else self.input.text()).strip()
        if not text:
            return
        self.input.clear()
        self.add_message("user", text)
        self.loop.submit(self.assistant.process(text, self._emit))

    async def _emit(self, ev: dict):
        # Runs on the async thread; hop to the GUI thread via the queued signal.
        self.bridge.event.emit(ev)

    def _open_settings(self):
        dlg = SettingsDialog(self.assistant, on_saved=self._refresh_status, parent=self)
        dlg.exec()

    def _toggle_wake(self):
        if self.wake and self.wake.isRunning():
            self.wake.stop(); self.wake = None
            self.wake_btn.setChecked(False); self.wake_btn.setText("  Wake: off")
            return
        self.wake = WakeListener(self.assistant.state().get("wake_word", "dexter"))
        if not self.wake.available:
            self.add_trace("Microphone/SpeechRecognition not available for background listening.", True)
            self.wake = None; self.wake_btn.setChecked(False); return
        self.wake.command.connect(lambda c: self._send(c))
        self.wake.state.connect(self._wake_state)
        self.wake.start()
        self.wake_btn.setChecked(True); self.wake_btn.setText("  Wake: on")

    def _wake_state(self, s: str):
        if s == "listening":
            self.orb.set_state("listening")
        elif s == "heard":
            self.orb.set_state("thinking")
        elif s in ("off", "error"):
            self.orb.set_state("idle")

    # ---- event handling (GUI thread) ----
    def on_event(self, ev: dict):
        t = ev.get("type")
        if t == "status":
            self.orb.set_state("thinking" if ev.get("state") == "thinking" else "idle")
        elif t == "thought":
            self.orb.set_caption(ev.get("text", "")[:80]); self.add_trace("• " + ev.get("text", ""))
        elif t == "action":
            self.orb.set_state("thinking"); self.add_trace(f"▶ {ev.get('tool')}", accent=CYAN)
        elif t == "observation":
            pass
        elif t == "speak":
            self.orb.set_state("speaking"); self.orb.set_caption(ev.get("text", "")[:80])
            self.add_message("dexter", ev.get("text", ""))
        elif t == "card":
            self.add_card(ev)
        elif t == "clear_cards":
            self.clear_cards()
        elif t == "task":
            self.upsert_task(ev.get("task", {}))
        elif t == "audio":
            self.play_wav(ev.get("wav", b""))
        elif t == "spoke":
            self.orb.set_state("speaking")
        elif t == "error":
            self.add_card({"id": "err", "title": "Error", "body": ev.get("message", ""), "accent": "red"})

    # ---- feed widgets ----
    def _insert(self, layout, widget):
        layout.insertWidget(layout.count() - 1, widget)

    def add_message(self, role: str, text: str):
        lbl = QLabel(text); lbl.setWordWrap(True)
        lbl.setObjectName("msgUser" if role == "user" else "msgDexter")
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        wrap = QHBoxLayout(); w = QWidget(); w.setLayout(wrap)
        wrap.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            wrap.addStretch(1); wrap.addWidget(lbl, 4)
        else:
            wrap.addWidget(lbl, 4); wrap.addStretch(1)
        self._insert(self.feed_layout, w)
        self._scroll_bottom(self.feed_area)

    def add_trace(self, text: str, err: bool = False, accent: str = None):
        lbl = QLabel(text); lbl.setObjectName("trace"); lbl.setWordWrap(True)
        if err:
            lbl.setStyleSheet(f"color:{DANGER};")
        elif accent:
            lbl.setStyleSheet(f"color:{accent};")
        self._insert(self.feed_layout, lbl)
        self._scroll_bottom(self.feed_area)

    def add_card(self, c: dict):
        frame = QFrame(); frame.setObjectName("card")
        v = QVBoxLayout(frame); v.setContentsMargins(12, 10, 12, 12); v.setSpacing(4)
        head = QHBoxLayout()
        title = QLabel(c.get("title", "Info")); title.setObjectName("cardTitle")
        accent = ACCENT.get(c.get("accent", "cyan"), CYAN)
        title.setStyleSheet(f"color:{accent};")
        x = QPushButton(); x.setFlat(True); x.setFixedSize(20, 20)
        x.setIcon(icons.icon("close", 14, INK_DIM))
        head.addWidget(title); head.addStretch(1); head.addWidget(x)
        v.addLayout(head)
        body = QLabel(c.get("body", "")); body.setObjectName("cardBody")
        body.setWordWrap(True); body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(body)
        frame.setStyleSheet(f"#card{{border:1px solid {accent};}}")
        cid = c.get("id", str(id(frame)))
        x.clicked.connect(lambda: self._remove_card(cid))
        self.cards[cid] = frame
        self._insert(self.feed_layout, frame)
        self._scroll_bottom(self.feed_area)

    def _remove_card(self, cid):
        w = self.cards.pop(cid, None)
        if w:
            w.setParent(None); w.deleteLater()

    def clear_cards(self):
        for cid in list(self.cards):
            self._remove_card(cid)

    def upsert_task(self, task: dict):
        tid = task.get("id")
        if not tid:
            return
        row = self.tasks.get(tid)
        if row is None:
            row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(2, 2, 2, 2); h.setSpacing(8)
            dot = QLabel("●"); lbl = QLabel("")
            lbl.setWordWrap(True)
            h.addWidget(dot); h.addWidget(lbl, 1)
            row._dot, row._lbl = dot, lbl
            self.tasks[tid] = row
            self._insert(self.tasks_layout, row)
        status = task.get("status", "pending")
        row._dot.setStyleSheet(f"color:{TASK_COLOR.get(status, INK_DIM)};")
        row._lbl.setText(task.get("title", ""))
        row._lbl.setStyleSheet(f"color:{INK_DIM};text-decoration:line-through;" if status == "done" else f"color:{INK};")
        self._scroll_bottom(self.tasks_area)

    def _scroll_bottom(self, area):
        bar = area.verticalScrollBar(); bar.setValue(bar.maximum())

    # ---- audio playback (Groq neural voice) ----
    def play_wav(self, data: bytes):
        if not data:
            return
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            from PySide6.QtCore import QUrl
        except Exception:
            self.add_trace("Audio playback module unavailable; install PySide6 multimedia.", True)
            return
        try:
            tmp = Path(tempfile.gettempdir()) / "dexter_tts.wav"
            tmp.write_bytes(data)
            if self.player is None:
                self.player = QMediaPlayer(self)
                self._audio_out = QAudioOutput(self)
                self.player.setAudioOutput(self._audio_out)
                self.player.playbackStateChanged.connect(
                    lambda s: self.orb.set_state("idle")
                    if s == QMediaPlayer.StoppedState else None)
            self._audio_out.setVolume(1.0)
            self.player.setSource(QUrl.fromLocalFile(str(tmp)))
            self.orb.set_state("speaking")
            self.player.play()
        except Exception as exc:
            self.add_trace(f"Audio playback failed: {exc}", True)

    def closeEvent(self, e):
        try:
            if self.wake:
                self.wake.stop()
            self.loop.stop()
        except Exception:
            pass
        super().closeEvent(e)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Dexter Cyber")
    icon_path = resource_path("assets/dexter.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    loop = AsyncLoop(); loop.start()
    assistant = Assistant()

    if not assistant.permissions.has_consented:
        dlg = ConsentDialog(assistant)
        dlg.setStyleSheet(QSS)
        if dlg.exec() != QDialog.Accepted:
            return 0

    win = DexterWindow(assistant, loop)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
