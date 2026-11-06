#!/usr/bin/env bash
# ============================================================
#  Build Dexter Cyber into a single executable.
#  On Linux this produces an ELF binary; on macOS a Mach-O binary.
#  (A Windows .exe must be built on Windows — use build.bat there,
#   or let the GitHub Actions workflow build it for you.)
# ============================================================
set -euo pipefail

echo "[1/3] Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller

echo "[2/3] Building DexterCyber with PyInstaller..."
python3 -m PyInstaller --noconfirm dexter_cyber.spec

echo "[3/3] Done."
echo
echo "  Your executable is here:  dist/DexterCyber"
echo "  Put a .env file (with OPENROUTER_API_KEY) next to it, then run it."
