"""System access: run shell commands and read/write files.

These are the highest-risk capabilities, so they are kept deliberately simple
and always pass through the permission layer before reaching this module.
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional


def run_command(command: str, cwd: Optional[str] = None, timeout: int = 60) -> str:
    """Run a shell command and return combined stdout/stderr (truncated)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"[timed out after {timeout}s]"
    except Exception as exc:  # pragma: no cover
        return f"[failed to run: {exc}]"

    out = (result.stdout or "") + (result.stderr or "")
    out = out.strip()
    if len(out) > 4000:
        out = out[:4000] + "\n…[output truncated]"
    return f"(exit {result.returncode})\n{out}" if out else f"(exit {result.returncode})"


def read_file(path: str, max_bytes: int = 20000) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"[no such file: {path}]"
    if not p.is_file():
        return f"[not a file: {path}]"
    try:
        data = p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"[could not read {path}: {exc}]"
    if len(data) > max_bytes:
        data = data[:max_bytes] + "\n…[truncated]"
    return data


def write_file(path: str, content: str, append: bool = False) -> str:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    try:
        with p.open(mode, encoding="utf-8") as fh:
            fh.write(content)
    except Exception as exc:
        return f"[could not write {path}: {exc}]"
    return f"{'Appended to' if append else 'Wrote'} {path} ({len(content)} chars)."


def list_dir(path: str = ".") -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"[no such path: {path}]"
    if p.is_file():
        return f"{p.name} (file, {p.stat().st_size} bytes)"
    entries = []
    for child in sorted(p.iterdir()):
        kind = "dir" if child.is_dir() else "file"
        entries.append(f"{child.name}\t[{kind}]")
    return "\n".join(entries) if entries else "[empty directory]"


def open_path(target: str) -> str:
    """Open a file, folder, URL or application using the OS default handler."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", target])
        elif system == "Windows":
            os.startfile(target)  # type: ignore[attr-defined]
        else:  # Linux and others
            subprocess.Popen(["xdg-open", target])
    except Exception as exc:
        return f"[could not open {target}: {exc}]"
    return f"Opened {target}."


def system_info() -> str:
    return (
        f"OS: {platform.system()} {platform.release()}\n"
        f"Machine: {platform.machine()}\n"
        f"Python: {platform.python_version()}\n"
        f"Working dir: {os.getcwd()}\n"
        f"User home: {Path.home()}"
    )
