"""Settings dialog: API keys, models, voice, wake word and capabilities."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from ..config import settings
from . import icons
from .theme import CYAN, INK_DIM, QSS


def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionLabel")
    return lbl


class SettingsDialog(QDialog):
    def __init__(self, assistant, on_saved, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.on_saved = on_saved
        self.setWindowTitle("Dexter Cyber — Settings")
        self.setMinimumWidth(560)
        self.setStyleSheet(QSS)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 20)
        outer.setSpacing(14)

        head = QLabel("Settings")
        head.setObjectName("panelHead")
        outer.addWidget(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoShape)
        body = QWidget()
        form = QVBoxLayout(body)
        form.setSpacing(10)

        # ---- API keys ----
        form.addWidget(_section("API KEYS"))
        key_row = QLabel("Keys are stored locally on this computer only.")
        key_row.setObjectName("hint")
        form.addWidget(key_row)

        self.openrouter = self._secret_field(settings.openrouter_api_key)
        self.groq = self._secret_field(settings.groq_api_key)
        f1 = QFormLayout(); f1.setSpacing(10)
        f1.addRow(self._keyed("OpenRouter key"), self.openrouter)
        f1.addRow(self._keyed("Groq key"), self.groq)
        form.addLayout(f1)
        link = QLabel('<a style="color:#35e4ff;" href="#">openrouter.ai/keys · console.groq.com/keys</a>')
        link.setObjectName("hint")
        form.addWidget(link)

        # ---- Models ----
        form.addWidget(_section("MODELS"))
        self.text_model = QLineEdit(settings.text_model)
        self.vision_model = QLineEdit(settings.vision_model)
        f2 = QFormLayout(); f2.setSpacing(10)
        f2.addRow("Text / brain", self.text_model)
        f2.addRow("Vision", self.vision_model)
        form.addLayout(f2)

        # ---- Voice ----
        form.addWidget(_section("VOICE"))
        self.engine = QComboBox()
        self.engine.addItem("System voice (offline)", "system")
        self.engine.addItem("Groq neural (Arabic / abdullah)", "groq")
        self.engine.setCurrentIndex(1 if settings.voice_engine == "groq" else 0)
        self.groq_voice = QLineEdit(settings.groq_voice)
        self.rate = QSpinBox(); self.rate.setRange(80, 320); self.rate.setValue(settings.voice_rate)
        f3 = QFormLayout(); f3.setSpacing(10)
        f3.addRow("Engine", self.engine)
        f3.addRow("Groq voice", self.groq_voice)
        f3.addRow("Rate (wpm)", self.rate)
        form.addLayout(f3)

        # ---- Wake word ----
        form.addWidget(_section("WAKE WORD"))
        self.wake = QLineEdit(settings.wake_word)
        f4 = QFormLayout(); f4.addRow("Wake word", self.wake)
        form.addLayout(f4)

        # ---- Capabilities ----
        form.addWidget(_section("CAPABILITIES"))
        self.caps = {}
        for cap in self.assistant.permissions.snapshot()["capabilities"]:
            cb = QCheckBox(f"{cap['title']}  ·  {cap['risk']}")
            cb.setChecked(cap["granted"])
            self.caps[cap["key"]] = cb
            form.addWidget(cb)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # ---- Actions ----
        row = QHBoxLayout()
        clear = QPushButton("  Clear memory"); clear.setObjectName("iconbtn")
        clear.setIcon(icons.icon("trash", 18, INK_DIM))
        clear.clicked.connect(self._clear_memory)
        revoke = QPushButton("  Revoke all & re-ask"); revoke.setObjectName("danger")
        revoke.setIcon(icons.icon("shield", 18, "#ff5a6a"))
        revoke.clicked.connect(self._revoke)
        row.addWidget(clear); row.addWidget(revoke); row.addStretch(1)
        save = QPushButton("Save"); save.setObjectName("primary")
        save.clicked.connect(self._save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        row.addWidget(close); row.addWidget(save)
        outer.addLayout(row)

    def _keyed(self, text):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0, 0, 0, 0); l.setSpacing(6)
        ic = QLabel(); ic.setPixmap(icons.pixmap("key", 16, CYAN)); l.addWidget(ic)
        l.addWidget(QLabel(text)); l.addStretch(1)
        return w

    def _secret_field(self, value: str) -> QLineEdit:
        e = QLineEdit(value)
        e.setEchoMode(QLineEdit.Password)
        e.setPlaceholderText("paste key…")
        show = e.addAction(icons.icon("eye", 16, INK_DIM), QLineEdit.TrailingPosition)
        show.triggered.connect(lambda: e.setEchoMode(
            QLineEdit.Normal if e.echoMode() == QLineEdit.Password else QLineEdit.Password))
        return e

    def _save(self):
        values = dict(
            openrouter_api_key=self.openrouter.text().strip(),
            groq_api_key=self.groq.text().strip(),
            text_model=self.text_model.text().strip(),
            vision_model=self.vision_model.text().strip(),
            voice_engine=self.engine.currentData(),
            groq_voice=self.groq_voice.text().strip(),
            voice_rate=self.rate.value(),
            wake_word=self.wake.text().strip().lower(),
        )
        self.assistant.apply_settings(values)
        for key, cb in self.caps.items():
            try:
                self.assistant.permissions.set_grant(key, cb.isChecked())
            except KeyError:
                pass
        if self.on_saved:
            self.on_saved()
        self.accept()

    def _clear_memory(self):
        self.assistant.memory.clear()

    def _revoke(self):
        self.assistant.permissions.reset()
        if self.on_saved:
            self.on_saved()
        self.accept()
