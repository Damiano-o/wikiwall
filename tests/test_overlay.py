import sys
import threading
import types
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from wikiwall import overlay
from wikiwall.overlay import box_contains, crop_box, is_clickable_window


def test_box_contains_inside_and_outside():
    box = (10.0, 20.0, 30.0, 40.0)
    assert box_contains(box, 25, 30)
    assert not box_contains(box, 5, 30)
    assert not box_contains(box, 25, 70)


def test_box_contains_uses_a_small_margin():
    box = (10.0, 20.0, 30.0, 40.0)
    assert box_contains(box, 8, 18, margin=2)
    assert not box_contains(box, 7, 18, margin=2)


def test_crop_box_extracts_the_requested_region(tmp_path: Path):
    path = tmp_path / "wallpaper.png"
    image = Image.new("RGB", (100, 100), (0, 0, 0))
    image.paste((255, 0, 0), (10, 20, 40, 60))
    image.save(path)

    crop = crop_box(path, (10.0, 20.0, 30.0, 40.0))

    assert crop.size == (30, 40)
    assert crop.getpixel((0, 0)) == (255, 0, 0)


def test_desktop_windows_are_clickable():
    for class_name in ("Progman", "WorkerW", "SHELLDLL_DefView", "SysListView32"):
        assert is_clickable_window(class_name, pid=123, own_pid=456)


def test_our_own_window_is_clickable():
    assert is_clickable_window("TkTopLevel", pid=456, own_pid=456)


def test_other_windows_are_not_clickable():
    assert not is_clickable_window("Notepad", pid=123, own_pid=456)
    assert not is_clickable_window(None, pid=None, own_pid=456)


def test_hotspot_works_even_when_desktop_is_not_foreground(monkeypatch):
    class FakeRoot:
        def withdraw(self):
            pass

        def after(self, _delay, _callback):
            pass

        def destroy(self):
            pass

    fake_tk = types.ModuleType("tkinter")
    fake_tk.Tk = FakeRoot
    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)

    class FakeHotspot:
        def __init__(self):
            self.shown = []

        def show(self, box, image=None):
            self.shown.append((box, image))

        def hide(self):
            pass

        def destroy(self):
            pass

    class FakeWatcher:
        clickable_qr = True
        current_url = "https://it.wikipedia.org/wiki/Test"
        current = SimpleNamespace(
            image_path=Path("wallpaper.png"),
            theme="paper",
            qr_box=(10.0, 20.0, 30.0, 40.0),
            link_box=(10.0, 70.0, 100.0, 20.0),
            skip_box=(10.0, 100.0, 80.0, 30.0),
        )

    fake_hotspot = FakeHotspot()
    overlay_window = overlay._Overlay(FakeWatcher(), threading.Event())
    monkeypatch.setattr(overlay, "is_desktop_foreground", lambda: False, raising=False)
    monkeypatch.setattr(overlay, "_cursor_position", lambda: (20, 110))
    monkeypatch.setattr(overlay_window, "_is_desktop_at", lambda _x, _y: True)
    monkeypatch.setattr(
        overlay_window,
        "_hotspot",
        lambda _kind, _state: fake_hotspot,
    )

    overlay_window._tick()

    assert fake_hotspot.shown == [((10.0, 100.0, 80.0, 30.0), None)]
    overlay_window.close()
