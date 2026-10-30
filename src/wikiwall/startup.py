from __future__ import annotations

import os
import sys
from pathlib import Path

STARTUP_FILENAME = "WikiWall.vbs"


class StartupError(RuntimeError):
    """Raised when the startup shortcut cannot be managed."""


def startup_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise StartupError("La variabile APPDATA non è impostata.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_path() -> Path:
    return startup_dir() / STARTUP_FILENAME


def pythonw_path() -> Path:
    executable = Path(sys.executable)
    if executable.name.lower() == "python.exe":
        candidate = executable.with_name("pythonw.exe")
        if candidate.is_file():
            return candidate
    return executable


def vbs_content(python: Path, working_dir: Path) -> str:
    return (
        'Set shell = CreateObject("WScript.Shell")\r\n'
        f'shell.CurrentDirectory = "{working_dir}"\r\n'
        f'shell.Run Chr(34) & "{python}" & Chr(34) & " -m wikiwall watch", 0, False\r\n'
    )


def install_startup(
    python: Path | None = None,
    working_dir: Path | None = None,
) -> Path:
    destination = startup_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    python = python or pythonw_path()
    working_dir = working_dir or Path.home()
    # VBScript is read reliably by Windows Script Host when saved as UTF-16.
    destination.write_text(vbs_content(python, working_dir), encoding="utf-16")
    return destination


def uninstall_startup() -> bool:
    destination = startup_path()
    try:
        destination.unlink()
    except FileNotFoundError:
        return False
    return True


__all__ = [
    "STARTUP_FILENAME",
    "StartupError",
    "install_startup",
    "pythonw_path",
    "startup_dir",
    "startup_path",
    "uninstall_startup",
    "vbs_content",
]
