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
HOTKEY_ID = 1


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
    """Listen for Ctrl+Alt+N in a dedicated Win32 message-loop thread."""

    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._running = threading.Event()

    @property
    def running(self) -> bool:
        return self._running.is_set()

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

    def _run(self) -> None:
        if not IS_WINDOWS:
            return

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = int(kernel32.GetCurrentThreadId())

        if not user32.RegisterHotKey(
            None,
            HOTKEY_ID,
            MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
            VK_N,
        ):
            LOGGER.warning(
                "Ctrl+Alt+N non disponibile: un'altra applicazione lo sta usando"
            )
            self._thread_id = None
            return

        self._running.set()
        LOGGER.info("Scorciatoia Ctrl+Alt+N attiva")
        try:
            message = _MSG()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY and message.wParam == HOTKEY_ID:
                    try:
                        self.callback()
                    except Exception:  # noqa: BLE001 - a callback must not kill the loop
                        LOGGER.exception("Errore nella scorciatoia globale")
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)
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


__all__ = ["HotkeyListener"]
