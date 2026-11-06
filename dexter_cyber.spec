# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for Dexter Cyber.

Produces a single self-contained executable (DexterCyber.exe on Windows,
DexterCyber on macOS/Linux) that bundles the Python runtime, all dependencies
and the web UI. Build with:

    pyinstaller --noconfirm dexter_cyber.spec

The resulting binary is in ./dist/.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# --- Collect dynamically-imported submodules so nothing is missing at runtime ---
hidden = [
    "dexter.server", "dexter.config", "dexter.ui_qt.app",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtMultimedia",
]
for pkg in ("uvicorn", "pyttsx3", "anyio", "httpx", "httpcore", "websockets", "comtypes"):
    try:
        hidden += collect_submodules(pkg)
    except Exception:
        # comtypes exists only on Windows; ignore where unavailable.
        pass

# --- Bundle the web UI and app assets (icon, etc.) ---
datas = [("dexter/web", "dexter/web"), ("assets", "assets")]

# --- Optional live mic-level support (sounddevice + its PortAudio lib) ---
binaries = []
try:
    from PyInstaller.utils.hooks import collect_dynamic_libs
    binaries += collect_dynamic_libs("sounddevice")
    datas += collect_data_files("sounddevice")
    hidden += ["sounddevice", "_sounddevice"]
except Exception:
    pass

# Optional custom icon (place assets/dexter.ico in the repo to use it).
_icon_path = Path("assets/dexter.ico")
icon = str(_icon_path) if _icon_path.exists() else None

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DexterCyber",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # show a console so startup errors are visible (diagnostic)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
