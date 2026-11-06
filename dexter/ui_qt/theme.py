"""Dark monochrome theme — black & gray (colors + Qt stylesheet)."""

BG = "#0a0a0b"
BG2 = "#060607"
PANEL = "#151518"
# "CYAN" is kept as the name of the primary accent, but it is now a near-white
# highlight so the whole UI reads as black & gray.
CYAN = "#e8eaed"
BLUE = "#5a5d63"      # mid-gray secondary
INK = "#e6e8ec"
INK_DIM = "#868b93"
DANGER = "#ff6b6b"
WARN = "#d8c07a"
OK = "#9fd8b0"
LINE = "rgba(255,255,255,0.10)"

QSS = f"""
* {{ font-family: "Segoe UI", "Noto Sans Arabic", system-ui, sans-serif; color: {INK}; }}
QWidget#root {{ background: {BG}; }}
QLabel {{ background: transparent; }}

#brand {{ font-size: 16px; font-weight: 700; letter-spacing: 3px; }}

QLineEdit, QPlainTextEdit {{
    background: #101013; border: 1px solid {LINE}; border-radius: 10px;
    padding: 10px 12px; selection-background-color: {BLUE};
}}
QLineEdit:focus {{ border: 1px solid rgba(255,255,255,0.35); }}

QPushButton {{
    background: #161619; border: 1px solid {LINE}; border-radius: 10px;
    padding: 9px 14px; color: {INK};
}}
QPushButton:hover {{ border: 1px solid rgba(255,255,255,0.35); background: #1c1c20; }}
QPushButton#primary {{ background: {CYAN}; color: #0a0a0b; font-weight: 700; border: none; }}
QPushButton#primary:hover {{ background: #ffffff; }}
QPushButton#danger {{ border: 1px solid {DANGER}; color: {DANGER}; }}
QPushButton#iconbtn {{ background: #141417; border: 1px solid {LINE}; border-radius: 11px; }}
QPushButton#pill {{ background: #141417; border: 1px solid {LINE}; border-radius: 16px; padding: 7px 14px; }}
QPushButton#pill:checked {{ background: {CYAN}; color: #0a0a0b; font-weight: 600; }}

#feed {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: #3a3a40; border-radius: 4px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: #4a4a52; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

#card {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 14px; }}
#cardTitle {{ color: {INK}; font-weight: 600; font-size: 13px; }}
#cardBody {{ color: {INK_DIM}; font-size: 12px; }}

#msgUser {{ background: #1b1b1f; border: 1px solid {LINE}; border-radius: 12px; padding: 9px 12px; }}
#msgDexter {{ background: #101013; border: 1px solid {LINE}; border-radius: 12px; padding: 9px 12px; }}
#trace {{ color: {INK_DIM}; font-size: 12px; }}

QDialog {{ background: {BG2}; }}
#panelHead {{ font-size: 18px; font-weight: 700; letter-spacing: 1px; }}
#sectionLabel {{ color: {INK_DIM}; font-size: 11px; letter-spacing: 3px; }}
#hint {{ color: {INK_DIM}; font-size: 12px; }}
#tasksHead {{ color: {INK_DIM}; font-size: 11px; letter-spacing: 3px; }}

QCheckBox {{ spacing: 8px; }}
QComboBox {{ background: #101013; border: 1px solid {LINE}; border-radius: 10px; padding: 8px 12px; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {LINE}; selection-background-color: {BLUE}; }}
QSpinBox {{ background: #101013; border: 1px solid {LINE}; border-radius: 10px; padding: 6px; }}
"""
