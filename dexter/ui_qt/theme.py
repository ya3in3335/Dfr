"""Dark monochrome theme — black & gray, soft rounded edges, 3D depth."""

BG = "#0a0a0b"
BG2 = "#060607"
PANEL = "#151518"
CYAN = "#e8eaed"      # primary accent = near-white (monochrome)
BLUE = "#5a5d63"
INK = "#e6e8ec"
INK_DIM = "#868b93"
DANGER = "#ff6b6b"
WARN = "#d8c07a"
OK = "#9fd8b0"
LINE = "rgba(255,255,255,0.09)"

QSS = f"""
* {{ font-family: "Segoe UI", "Noto Sans Arabic", system-ui, sans-serif; color: {INK}; }}
QWidget#root {{ background: {BG}; }}
QLabel {{ background: transparent; }}

#brand {{ font-size: 16px; font-weight: 700; letter-spacing: 3px; }}

/* inset inputs (recessed 3D) */
QLineEdit, QPlainTextEdit {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #0a0a0c, stop:1 #141418);
    border: 1px solid rgba(0,0,0,0.6);
    border-top: 1px solid rgba(0,0,0,0.8);
    border-radius: 14px; padding: 11px 14px; selection-background-color: {BLUE};
}}
QLineEdit:focus {{ border: 1px solid rgba(255,255,255,0.32); }}

/* raised 3D buttons */
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #24242a, stop:1 #151519);
    border: 1px solid {LINE}; border-top: 1px solid rgba(255,255,255,0.14);
    border-radius: 14px; padding: 10px 16px; color: {INK};
}}
QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2c2c33, stop:1 #1b1b20); }}
QPushButton:pressed {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #141418, stop:1 #202026);
    border-top: 1px solid rgba(0,0,0,0.6); padding-top: 11px; }}
QPushButton#primary {{ color: #0a0a0b; font-weight: 700; border: none;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #c7ccd2); }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #d8dce1); }}
QPushButton#primary:pressed {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #cfd3d8, stop:1 #e9ebee); }}
QPushButton#danger {{ border: 1px solid {DANGER}; color: {DANGER};
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #241416, stop:1 #190f11); }}
QPushButton#iconbtn {{ border-radius: 14px;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #222228, stop:1 #141418);
    border: 1px solid {LINE}; border-top: 1px solid rgba(255,255,255,0.12); }}
QPushButton#pill {{ border-radius: 18px; padding: 8px 15px;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #222228, stop:1 #141418);
    border: 1px solid {LINE}; border-top: 1px solid rgba(255,255,255,0.12); }}
QPushButton#pill:checked {{ color: #0a0a0b; font-weight: 600;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #c7ccd2); border: none; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #3a3a40; border-radius: 4px; min-height: 26px; }}
QScrollBar::handle:vertical:hover {{ background: #4a4a52; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

/* raised 3D panel wrapper (activity / tasks) */
#panelCard {{ border-radius: 20px; border: 1px solid {LINE};
    border-top: 1px solid rgba(255,255,255,0.10);
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #161619, stop:1 #0d0d10); }}

/* raised 3D cards */
#card {{ border-radius: 18px; border: 1px solid {LINE};
    border-top: 1px solid rgba(255,255,255,0.12);
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1d1d22, stop:1 #121216); }}
#cardTitle {{ color: {INK}; font-weight: 600; font-size: 13px; }}
#cardBody {{ color: {INK_DIM}; font-size: 12px; }}

/* chat bubbles with soft edges + subtle depth */
#msgUser {{ border-radius: 16px; padding: 10px 13px; border: 1px solid {LINE};
    border-top: 1px solid rgba(255,255,255,0.12);
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #26262c, stop:1 #1a1a1f); }}
#msgDexter {{ border-radius: 16px; padding: 10px 13px; border: 1px solid {LINE};
    border-top: 1px solid rgba(255,255,255,0.08);
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #151519, stop:1 #0e0e12); }}
#trace {{ color: {INK_DIM}; font-size: 12px; }}

QDialog {{ background: {BG2}; }}
#panel, .panel {{ border-radius: 22px; }}
#panelHead {{ font-size: 18px; font-weight: 700; letter-spacing: 1px; }}
#sectionLabel {{ color: {INK_DIM}; font-size: 11px; letter-spacing: 3px; }}
#hint {{ color: {INK_DIM}; font-size: 12px; }}
#tasksHead {{ color: {INK_DIM}; font-size: 11px; letter-spacing: 3px; }}

QCheckBox {{ spacing: 8px; }}
QComboBox {{ border-radius: 12px; padding: 9px 12px; border: 1px solid {LINE};
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1d1d22, stop:1 #141418); }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {LINE};
    border-radius: 10px; selection-background-color: {BLUE}; }}
QSpinBox {{ border-radius: 12px; padding: 7px; border: 1px solid {LINE};
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1d1d22, stop:1 #141418); }}

.veng {{ border-radius: 14px; }}
"""
