from __future__ import annotations

import ctypes
import logging
import sys
import threading
from collections.abc import Callable
from ctypes import wintypes

LOGGER = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_N = 0x4E
VK_O = 0x4F

#: Ctrl+Alt+N: skip to the next article.
HOTKEY_ID = 1
#: Ctrl+Alt+O: switch WikiWall on or off.
TOGGLE_HOTKEY_ID = 2

HOTKEY_NAMES = {
    HOTKEY_ID: "Ctrl+Alt+N",
    TOGGLE_HOTKEY_ID: "Ctrl+Alt+O",
}


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class HotkeyListener:
    """Listen for global shortcuts in a dedicated Win32 message-loop thread."""

    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self._bindings: dict[int, tuple[int, int, Callable[[], None]]] = {
            HOTKEY_ID: (MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_N, callback),
        }
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._running = threading.Event()

    @property
    def running(self) -> bool:
        return self._running.is_set()

    @property
    def bindings(self) -> dict[int, tuple[int, int, Callable[[], None]]]:
        return dict(self._bindings)

    def add(
        self,
        hotkey_id: int,
        modifiers: int,
        vk: int,
        callback: Callable[[], None],
    ) -> None:
        """Register an extra global shortcut. Must happen before ``start()``."""
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Aggiungi le scorciatoie prima di avviare il listener.")
        self._bindings[int(hotkey_id)] = (
            int(modifiers) | MOD_NOREPEAT,
            int(vk),
            callback,
        )

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return True
        self._thread = threading.Thread(
            target=self._run,
            name="wikiwall-hotkey",
            daemon=True,
        )
        self._thread.start()
        return True

    @staticmethod
    def _label(hotkey_id: int, modifiers: int, vk: int) -> str:
        name = HOTKEY_NAMES.get(hotkey_id)
        if name is not None:
            return name
        parts = []
        if modifiers & MOD_CONTROL:
            parts.append("Ctrl")
        if modifiers & MOD_ALT:
            parts.append("Alt")
        if modifiers & 0x0004:  # MOD_SHIFT
            parts.append("Shift")
        parts.append(chr(vk) if 0x30 <= vk <= 0x5A else f"VK {vk}")
        return "+".join(parts)

    def _run(self) -> None:
        if not IS_WINDOWS:
            return

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = int(kernel32.GetCurrentThreadId())

        registered: list[int] = []
        for hotkey_id, (modifiers, vk, _callback) in self._bindings.items():
            if user32.RegisterHotKey(None, hotkey_id, modifiers, vk):
                registered.append(hotkey_id)
                LOGGER.info("Scorciatoia %s attiva", self._label(hotkey_id, modifiers, vk))
            else:
                LOGGER.warning(
                    "Scorciatoia %s non disponibile: un'altra applicazione la sta usando",
                    self._label(hotkey_id, modifiers, vk),
                )

        if not registered:
            self._thread_id = None
            return

        self._running.set()
        try:
            message = _MSG()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message != WM_HOTKEY:
                    continue
                binding = self._bindings.get(int(message.wParam))
                if binding is None:
                    continue
                try:
                    binding[2]()
                except Exception:  # noqa: BLE001 - a callback must not kill the loop
                    LOGGER.exception("Errore nella scorciatoia globale")
        finally:
            for hotkey_id in registered:
                user32.UnregisterHotKey(None, hotkey_id)
            self._running.clear()
            self._thread_id = None

    def stop(self) -> None:
        thread_id = self._thread_id
        if thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
            except Exception:  # noqa: BLE001 - shutdown is best effort
                LOGGER.debug("Impossibile fermare il thread della scorciatoia", exc_info=True)
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        self._running.clear()


__all__ = [
    "HOTKEY_ID",
    "HOTKEY_NAMES",
    "MOD_ALT",
    "MOD_CONTROL",
    "MOD_NOREPEAT",
    "TOGGLE_HOTKEY_ID",
    "VK_N",
    "VK_O",
    "HotkeyListener",
]
