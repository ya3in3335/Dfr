"""Dark JARVIS theme (colors + Qt stylesheet)."""

BG = "#040912"
BG2 = "#02060d"
PANEL = "#0a1420"
CYAN = "#35e4ff"
BLUE = "#2f7bff"
INK = "#dfeefc"
INK_DIM = "#7fa0b8"
DANGER = "#ff5a6a"
WARN = "#ffc24b"
OK = "#49ffb0"
LINE = "rgba(53,228,255,0.22)"

QSS = f"""
* {{ font-family: "Segoe UI", "Noto Sans Arabic", system-ui, sans-serif; color: {INK}; }}
QWidget#root {{ background: {BG}; }}
QLabel {{ background: transparent; }}

#brand {{ font-size: 16px; font-weight: 700; letter-spacing: 2px; }}
#brandCyan {{ color: {CYAN}; }}

QLineEdit, QPlainTextEdit {{
    background: rgba(4,12,20,0.9); border: 1px solid {LINE}; border-radius: 10px;
    padding: 10px 12px; selection-background-color: {BLUE};
}}
QLineEdit:focus {{ border: 1px solid {CYAN}; }}

QPushButton {{
    background: rgba(53,228,255,0.08); border: 1px solid {LINE}; border-radius: 10px;
    padding: 9px 14px; color: {INK};
}}
QPushButton:hover {{ border: 1px solid {CYAN}; }}
QPushButton#primary {{ background: {CYAN}; color: #04121a; font-weight: 700; border: none; }}
QPushButton#primary:hover {{ background: #6cf0ff; }}
QPushButton#danger {{ border: 1px solid {DANGER}; color: {DANGER}; }}
QPushButton#iconbtn {{ background: rgba(8,20,32,0.7); border: 1px solid {LINE}; border-radius: 11px; }}
QPushButton#pill {{ background: rgba(8,20,32,0.7); border: 1px solid {LINE}; border-radius: 16px; padding: 7px 14px; }}
QPushButton#pill:checked {{ background: {CYAN}; color: #04121a; font-weight: 600; }}

#feed {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: {BLUE}; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

#card {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 14px; }}
#cardTitle {{ color: {CYAN}; font-weight: 600; font-size: 13px; }}
#cardBody {{ color: {INK}; font-size: 12px; }}

#msgUser {{ background: rgba(53,228,255,0.12); border: 1px solid {LINE}; border-radius: 12px; padding: 9px 12px; }}
#msgDexter {{ background: rgba(6,18,28,0.9); border: 1px solid {LINE}; border-radius: 12px; padding: 9px 12px; }}
#trace {{ color: {INK_DIM}; font-size: 12px; }}

QDialog {{ background: {BG2}; }}
#panelHead {{ font-size: 18px; font-weight: 700; letter-spacing: 1px; }}
#sectionLabel {{ color: {CYAN}; font-size: 11px; letter-spacing: 3px; }}
#hint {{ color: {INK_DIM}; font-size: 12px; }}
#tasksHead {{ color: {CYAN}; font-size: 11px; letter-spacing: 3px; }}

QCheckBox {{ spacing: 8px; }}
QComboBox {{ background: rgba(4,12,20,0.9); border: 1px solid {LINE}; border-radius: 10px; padding: 8px 12px; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {LINE}; selection-background-color: {BLUE}; }}
QSpinBox {{ background: rgba(4,12,20,0.9); border: 1px solid {LINE}; border-radius: 10px; padding: 6px; }}
"""
