from __future__ import annotations

import ctypes
import logging
import os
import threading
import webbrowser
from ctypes import wintypes
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

from .wallpaper import IS_WINDOWS

if TYPE_CHECKING:
    from .watcher import Watcher

LOGGER = logging.getLogger(__name__)

Box = tuple[float, float, float, float]
DESKTOP_CLASSES = {"Progman", "WorkerW", "SHELLDLL_DefView", "SysListView32"}
LVM_HITTEST = 0x1012

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

class _LVHITTESTINFO(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("flags", wintypes.UINT),
        ("iItem", ctypes.c_int),
        ("iSubItem", ctypes.c_int),
        ("iGroup", ctypes.c_int),
    ]


_USER32: Any | None = None


def _user32() -> Any:
    """Return user32 with pointer-sized signatures configured once."""
    global _USER32
    if _USER32 is None:
        user32 = ctypes.windll.user32
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.restype = ctypes.c_int
        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        user32.GetCursorPos.restype = wintypes.BOOL
        user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        user32.SetWindowLongW.restype = ctypes.c_long
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL
        user32.ScreenToClient.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.POINT),
        ]
        user32.ScreenToClient.restype = wintypes.BOOL
        user32.SendMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.SendMessageW.restype = ctypes.c_ssize_t
        _USER32 = user32
    return _USER32


def box_contains(box: Box, x: float, y: float, margin: float = 0.0) -> bool:
    left, top, width, height = box
    return (
        left - margin <= x <= left + width + margin
        and top - margin <= y <= top + height + margin
    )


def crop_box(image_path: Path, box: Box) -> Image.Image:
    """Crop a region from the rendered wallpaper, clamped to the image."""
    left, top, width, height = box
    with Image.open(image_path) as image:
        x0 = max(0, int(round(left)))
        y0 = max(0, int(round(top)))
        x1 = min(image.width, int(round(left + width)))
        y1 = min(image.height, int(round(top + height)))
        return image.crop((x0, y0, x1, y1)).convert("RGB")


def is_clickable_window(class_name: str | None, pid: int | None, own_pid: int) -> bool:
    """A target is clickable over the desktop or over our own overlay."""
    if class_name in DESKTOP_CLASSES:
        return True
    return pid is not None and pid == own_pid


def _window_class(hwnd: int) -> str | None:
    if not IS_WINDOWS or not hwnd:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(256)
        length = _user32().GetClassNameW(wintypes.HWND(hwnd), buffer, 256)
        return buffer.value if length else None
    except Exception:  # noqa: BLE001 - Win32 probing is best effort
        return None


def _window_pid(hwnd: int) -> int | None:
    if not IS_WINDOWS or not hwnd:
        return None
    try:
        pid = wintypes.DWORD()
        _user32().GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(pid))
        return int(pid.value) or None
    except Exception:  # noqa: BLE001
        return None


def _window_at(x: int, y: int) -> int:
    if not IS_WINDOWS:
        return 0
    try:
        point = wintypes.POINT(x, y)
        hwnd = _user32().WindowFromPoint(point)
        return int(hwnd or 0)
    except Exception:  # noqa: BLE001
        return 0


def _cursor_position() -> tuple[int, int] | None:
    if not IS_WINDOWS:
        return None
    try:
        point = wintypes.POINT()
        if not _user32().GetCursorPos(ctypes.byref(point)):
            return None
        return int(point.x), int(point.y)
    except Exception:  # noqa: BLE001
        return None


def _desktop_icon_at(hwnd: int, x: int, y: int) -> bool:
    """True when the point is over an icon in the desktop list view."""
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        user32 = _user32()
        point = wintypes.POINT(x, y)
        user32.ScreenToClient(wintypes.HWND(hwnd), ctypes.byref(point))
        info = _LVHITTESTINFO()
        info.pt = point
        result = user32.SendMessageW(
            wintypes.HWND(hwnd),
            LVM_HITTEST,
            0,
            ctypes.byref(info),
        )
        return int(result) != -1 and info.iItem >= 0
    except Exception:  # noqa: BLE001 - icon probing is best effort
        return False


def _enable_dpi_awareness() -> None:
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001 - older Windows versions lack shcore
        pass


def _set_no_activate(hwnd: int) -> None:
    if not IS_WINDOWS or not hwnd:
        return
    try:
        user32 = _user32()
        handle = wintypes.HWND(hwnd)
        style = user32.GetWindowLongW(handle, GWL_EXSTYLE)
        user32.SetWindowLongW(
            handle,
            GWL_EXSTYLE,
            style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
        )
    except Exception:  # noqa: BLE001
        LOGGER.debug("Impossibile impostare lo stile dell'overlay", exc_info=True)


def _show_no_activate(hwnd: int, box: Box) -> None:
    if not IS_WINDOWS or not hwnd:
        return
    x, y, width, height = (int(round(value)) for value in box)
    try:
        user32 = _user32()
        handle = wintypes.HWND(hwnd)
        placed = user32.SetWindowPos(
            handle,
            wintypes.HWND(HWND_TOPMOST),
            x,
            y,
            width,
            height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        shown = user32.ShowWindow(handle, SW_SHOWNOACTIVATE)
        LOGGER.debug(
            "Overlay hwnd=%s pos=%s SetWindowPos=%s ShowWindow=%s",
            hwnd,
            (x, y, width, height),
            placed,
            shown,
        )
    except Exception:  # noqa: BLE001
        LOGGER.debug("Impossibile mostrare l'overlay", exc_info=True)


def _hide_window(hwnd: int) -> None:
    if not IS_WINDOWS or not hwnd:
        return
    try:
        _user32().ShowWindow(wintypes.HWND(hwnd), SW_HIDE)
    except Exception:  # noqa: BLE001
        pass


class _Hotspot:
    """A tiny frameless window aligned with one element of the wallpaper."""

    def __init__(
        self,
        root: Any,
        kind: str,
        callback: Any,
        accent: str,
        qr_bg: str,
    ) -> None:
        import tkinter as tk

        self.kind = kind
        self.callback = callback
        self.accent = accent
        self._tk = tk
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        try:
            self.window.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        self.window.configure(
            bg=qr_bg if kind == "qr" else "#010203",
            cursor="hand2",
        )
        if kind != "qr":
            self.window.attributes("-alpha", 0.01)
        self.canvas = tk.Canvas(
            self.window,
            highlightthickness=0,
            bd=0,
            bg=qr_bg if kind == "qr" else "#010203",
            cursor="hand2",
        )
        self.canvas.pack(fill="both", expand=True)
        self.window.withdraw()
        self.window.update_idletasks()
        self.hwnd = int(self.window.wm_frame(), 16)
        _set_no_activate(self.hwnd)
        self._photo: Any = None
        self.window.bind("<Button-1>", self._click)

    def _click(self, _event: Any = None) -> None:
        LOGGER.info("Click sull'hotspot %s", self.kind)
        self.callback()

    def show(self, box: Box, image: Image.Image | None = None) -> None:
        x, y, width, height = (int(round(value)) for value in box)
        LOGGER.debug("Mostro hotspot %s hwnd=%s box=%s", self.kind, self.hwnd, box)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.canvas.configure(width=width, height=height)
        if self.kind == "qr" and image is not None:
            from PIL import ImageTk

            self._photo = ImageTk.PhotoImage(image)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
            self.canvas.create_rectangle(
                1,
                1,
                width - 1,
                height - 1,
                outline=self.accent,
                width=2,
            )
        self.window.update_idletasks()
        _show_no_activate(self.hwnd, (x, y, width, height))

    def hide(self) -> None:
        _hide_window(self.hwnd)

    def destroy(self) -> None:
        try:
            self.window.destroy()
        except Exception:  # noqa: BLE001 - shutdown is best effort
            pass


class _Overlay:
    def __init__(self, watcher: Watcher, stop_event: threading.Event) -> None:
        import tkinter as tk

        from .template import THEMES

        self.watcher = watcher
        self.stop_event = stop_event
        self.themes = THEMES
        self.root = tk.Tk()
        self.root.withdraw()
        self._hotspots: dict[str, _Hotspot] = {}
        self._visible: str | None = None
        self._state_key: tuple[Any, ...] | None = None
        self.root.after(80, self._tick)

    def _current_state(self) -> Any:
        return self.watcher.current

    def _state_signature(self, state: Any) -> tuple[Any, ...]:
        return (
            state.image_path,
            state.theme,
            state.qr_box,
            state.link_box,
            state.skip_box,
        )

    def _hide_all(self) -> None:
        for hotspot in self._hotspots.values():
            hotspot.hide()
        self._visible = None

    def _hotspot(self, kind: str, state: Any) -> _Hotspot | None:
        box = getattr(state, f"{kind}_box", None)
        if box is None:
            return None
        if kind not in self._hotspots:
            palette = self.themes.get(state.theme, self.themes["paper"])
            if kind in {"qr", "link"}:
                callback = self._open_link
            else:
                callback = self._skip
            self._hotspots[kind] = _Hotspot(
                self.root,
                kind,
                callback,
                palette["accent"],
                palette["qr_bg"],
            )
        return self._hotspots[kind]

    def _open_link(self) -> None:
        LOGGER.info("Apertura voce dall'overlay")
        self._hide_all()
        try:
            webbrowser.open(self.watcher.current_url)
        except Exception:  # noqa: BLE001 - opening a browser is best effort
            LOGGER.exception("Impossibile aprire la voce nel browser")

    def _skip(self) -> None:
        self._hide_all()
        threading.Thread(
            target=self.watcher.skip_current,
            name="wikiwall-skip",
            daemon=True,
        ).start()

    def _is_desktop_at(self, x: int, y: int) -> bool:
        hwnd = _window_at(x, y)
        class_name = _window_class(hwnd)
        pid = _window_pid(hwnd)
        if class_name == "SysListView32" and pid != os.getpid():
            return not _desktop_icon_at(hwnd, x, y)
        return is_clickable_window(class_name, pid, os.getpid())

    def _tick(self) -> None:
        if self.stop_event.is_set():
            self.close()
            return

        try:
            if not self.watcher.clickable_qr:
                self._hide_all()
                self.root.after(120, self._tick)
                return

            state = self._current_state()
            if state is None:
                self._hide_all()
                self.root.after(120, self._tick)
                return

            signature = self._state_signature(state)
            if self._state_key != signature:
                self._hide_all()
                self._state_key = signature

            cursor = _cursor_position()
            if cursor is None:
                self._hide_all()
                self.root.after(120, self._tick)
                return

            x, y = cursor
            target = None
            for kind in ("qr", "link", "skip"):
                box = getattr(state, f"{kind}_box", None)
                if box is not None and box_contains(box, x, y, margin=3):
                    target = kind
                    break

            if target is None:
                self._hide_all()
            elif target != self._visible:
                self._hide_all()
                if self._is_desktop_at(x, y):
                    hotspot = self._hotspot(target, state)
                    if hotspot is not None:
                        box = getattr(state, f"{target}_box")
                        image = crop_box(state.image_path, box) if target == "qr" else None
                        hotspot.show(box, image)
                        self._visible = target
        except Exception:  # noqa: BLE001 - the overlay must never kill the watcher
            LOGGER.exception("Errore nell'overlay cliccabile")
            self._hide_all()
        finally:
            if not self.stop_event.is_set():
                try:
                    self.root.after(120, self._tick)
                except Exception:  # noqa: BLE001 - root may be closing
                    pass

    def close(self) -> None:
        self._hide_all()
        for hotspot in self._hotspots.values():
            hotspot.destroy()
        self._hotspots.clear()
        try:
            self.root.destroy()
        except Exception:  # noqa: BLE001
            pass


def run_overlay(watcher: Watcher, stop_event: threading.Event) -> None:
    """Run the clickable overlay in a dedicated thread."""
    if not IS_WINDOWS:
        return
    _enable_dpi_awareness()
    try:
        overlay = _Overlay(watcher, stop_event)
    except Exception:  # noqa: BLE001 - Tkinter may be unavailable
        LOGGER.exception("Overlay cliccabile non disponibile")
        return
    try:
        overlay.root.mainloop()
    except Exception:  # noqa: BLE001
        LOGGER.exception("Overlay cliccabile terminato con errore")
    finally:
        overlay.close()


__all__ = ["box_contains", "crop_box", "is_clickable_window", "run_overlay"]
