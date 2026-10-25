#!/usr/bin/env python3
"""Builds the backend into a single executable used by the desktop app as a sidecar.

Usage (from the repository root):  uv run --project backend --with pyinstaller python scripts/build_sidecar.py

Output: apps/desktop/src-tauri/binaries/caneca-server-<rust target triple>[.exe]
(Tauri's `externalBin` requires the target-triple suffix.)
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
OUT_DIR = ROOT / "apps" / "desktop" / "src-tauri" / "binaries"


def target_triple() -> str:
    try:
        out = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True).stdout
        for line in out.splitlines():
            if line.startswith("host:"):
                return line.split(":", 1)[1].strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}.get(machine, machine)
    if sys.platform.startswith("win"):
        return f"{arch}-pc-windows-msvc"
    if sys.platform == "darwin":
        return f"{arch}-apple-darwin"
    return f"{arch}-unknown-linux-gnu"


def main() -> int:
    sep = ";" if os.name == "nt" else ":"
    work = ROOT / "build" / "sidecar"
    entry = work / "entry.py"
    work.mkdir(parents=True, exist_ok=True)
    entry.write_text("from caneca.main import run\n\nif __name__ == '__main__':\n    run()\n", encoding="utf-8")
    pkg = BACKEND / "caneca"
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--name", "caneca-server",
        "--distpath", str(work / "dist"), "--workpath", str(work / "build"), "--specpath", str(work),
        "--add-data", f"{pkg / 'game' / 'content'}{sep}caneca/game/content",
        "--add-data", f"{pkg / 'persistence' / 'migrations'}{sep}caneca/persistence/migrations",
        "--collect-submodules", "caneca",
        "--hidden-import", "uvicorn.logging", "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto", "--hidden-import", "uvicorn.lifespan.on",
        str(entry),
    ]
    subprocess.run(cmd, check=True, cwd=BACKEND)
    exe = "caneca-server.exe" if os.name == "nt" else "caneca-server"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if os.name == "nt" else ""
    target = OUT_DIR / f"caneca-server-{target_triple()}{suffix}"
    shutil.copy2(work / "dist" / exe, target)
    print(f"sidecar: {target} ({target.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
