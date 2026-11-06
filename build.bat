@echo off
REM ============================================================
REM  Build Dexter Cyber into a single Windows executable (.exe)
REM ============================================================
setlocal

echo [1/3] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :err

echo [2/3] Building DexterCyber.exe with PyInstaller...
python -m PyInstaller --noconfirm dexter_cyber.spec
if errorlevel 1 goto :err

echo [3/3] Done.
echo.
echo   Your executable is here:  dist\DexterCyber.exe
echo   Put a .env file (with OPENROUTER_API_KEY) next to it, then double-click.
echo.
goto :eof

:err
echo.
echo Build failed. Make sure Python 3.10+ is installed and on PATH.
exit /b 1
