from __future__ import annotations

import ctypes
import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDWININICHANGE = 0x02

DEFAULT_SCREEN_SIZE = (1920, 1080)


class WallpaperError(RuntimeError):
    """Raised when Windows cannot apply the wallpaper."""


def get_screen_size(default: tuple[int, int] = DEFAULT_SCREEN_SIZE) -> tuple[int, int]:
    """Return the primary monitor size in physical pixels."""
    if not IS_WINDOWS:
        return default

    try:
        # Make GetSystemMetrics report physical pixels instead of scaled ones.
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001 - older Windows versions lack shcore
        pass

    try:
        width = int(ctypes.windll.user32.GetSystemMetrics(0))
        height = int(ctypes.windll.user32.GetSystemMetrics(1))
    except Exception:  # noqa: BLE001 - defensive: never break on a weird session
        return default

    if width <= 0 or height <= 0:
        return default
    return width, height


def _set_wallpaper_fill() -> None:
    """Ask Windows to stretch the image across the desktop (WallpaperStyle=10)."""
    if not IS_WINDOWS:
        return
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "10")
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
        finally:
            winreg.CloseKey(key)
    except OSError as exc:
        LOGGER.warning("Impossibile impostare lo stile dello sfondo: %s", exc)


def _set_wallpaper_native(path: Path) -> bool:
    if not IS_WINDOWS:
        return False
    return bool(
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            str(path),
            SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE,
        )
    )


def set_wallpaper(path: Path | str) -> None:
    """Apply an image as the Windows desktop wallpaper."""
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise WallpaperError(f"Immagine non trovata: {resolved}")
    if not IS_WINDOWS:
        raise WallpaperError("WikiWall supporta solo Windows per ora.")

    _set_wallpaper_fill()
    if not _set_wallpaper_native(resolved):
        raise WallpaperError("Windows non ha accettato il nuovo sfondo.")


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


def get_idle_seconds() -> float:
    """Seconds since the last keyboard or mouse input."""
    if not IS_WINDOWS:
        return 0.0

    try:
        info = _LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        tick = ctypes.windll.kernel32.GetTickCount()
        return max(0.0, (int(tick) - int(info.dwTime)) / 1000.0)
    except Exception:  # noqa: BLE001 - idle detection is best effort
        return 0.0


def is_desktop_foreground() -> bool:
    """True when the Windows desktop itself owns the foreground."""
    if not IS_WINDOWS:
        return False

    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buffer, 256)
        return buffer.value in {"Progman", "WorkerW"}
    except Exception:  # noqa: BLE001 - foreground detection is best effort
        return False


__all__ = [
    "WallpaperError",
    "get_idle_seconds",
    "get_screen_size",
    "is_desktop_foreground",
    "set_wallpaper",
]
