"""Build the mk3 desktop preview as a Windows executable with PyInstaller."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRYPOINT = ROOT / "desktop_app.py"
UI_DIR = ROOT / "ui"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_DIR = ROOT / "packaging"
APP_NAME = "iPodSyncStudio-mk3"


def main() -> None:
    if not ENTRYPOINT.exists():
        raise FileNotFoundError(f"No existe el entrypoint: {ENTRYPOINT}")
    if not UI_DIR.exists():
        raise FileNotFoundError(f"No existe la carpeta de UI: {UI_DIR}")

    if importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError(
            "PyInstaller no está instalado. Ejecuta `pip install -r mk3/requirements.txt` "
            "en Windows para generar el .exe."
        )

    separator = ";" if sys.platform.startswith("win") else ":"
    add_data = f"{UI_DIR}{separator}ui"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--add-data",
        add_data,
        str(ENTRYPOINT),
    ]

    print("Ejecutando build EXE:")
    print(" ".join(command))
    subprocess.run(command, check=True)
    print(f"\nBuild terminado. Revisa: {DIST_DIR}")


if __name__ == "__main__":
    main()
