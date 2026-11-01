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


class _FakeRoot:
    def withdraw(self):
        pass

    def after(self, _delay, _callback):
        pass

    def destroy(self):
        pass


class _FakeHotspot:
    def __init__(self):
        self.shown = []
        self.hides = 0
        self.destroyed = False

    def show(self, box, image=None):
        self.shown.append((box, image))

    def hide(self):
        self.hides += 1

    def destroy(self):
        self.destroyed = True


def _overlay_with_fakes(monkeypatch, state, hotspot):
    fake_tk = types.ModuleType("tkinter")
    fake_tk.Tk = _FakeRoot
    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)

    class FakeWatcher:
        clickable_qr = True
        current_url = state.article.url
        current = state

        def skip_current(self):
            return True

    window = overlay._Overlay(FakeWatcher(), threading.Event())
    monkeypatch.setattr(window, "_hotspot", lambda _kind, _state: hotspot)
    return window


def _state(tmp_path, url="https://it.wikipedia.org/wiki/Test"):
    image = tmp_path / "wallpaper.png"
    Image.new("RGB", (120, 160), (10, 10, 10)).save(image)
    return SimpleNamespace(
        image_path=image,
        theme="paper",
        qr_box=(10.0, 20.0, 30.0, 40.0),
        link_box=(10.0, 70.0, 100.0, 20.0),
        skip_box=(10.0, 100.0, 80.0, 30.0),
        article=SimpleNamespace(url=url),
    )


def test_hotspots_exist_before_the_pointer_arrives(monkeypatch, tmp_path):
    state = _state(tmp_path)
    hotspot = _FakeHotspot()
    window = _overlay_with_fakes(monkeypatch, state, hotspot)
    monkeypatch.setattr(overlay, "is_desktop_foreground", lambda: True)

    window._tick()

    assert [box for box, _image in hotspot.shown] == [
        state.qr_box,
        state.link_box,
        state.skip_box,
    ]
    assert hotspot.shown[0][1] is not None  # il QR viene ritagliato dallo sfondo
    window.close()


def test_hotspots_hide_when_an_app_takes_the_foreground(monkeypatch, tmp_path):
    state = _state(tmp_path)
    hotspot = _FakeHotspot()
    window = _overlay_with_fakes(monkeypatch, state, hotspot)
    monkeypatch.setattr(overlay, "is_desktop_foreground", lambda: False)

    window._tick()

    assert hotspot.shown == []
    window.close()


def test_qr_crop_is_cached_between_ticks(monkeypatch, tmp_path):
    state = _state(tmp_path)
    hotspot = _FakeHotspot()
    window = _overlay_with_fakes(monkeypatch, state, hotspot)
    monkeypatch.setattr(overlay, "is_desktop_foreground", lambda: True)

    window._tick()
    window._tick()

    assert len(window._crop_cache) == 1
    first_tick, second_tick = hotspot.shown[:3], hotspot.shown[3:]
    assert first_tick[0][1] is second_tick[0][1]
    window.close()


def test_a_new_article_invalidates_the_state(monkeypatch, tmp_path):
    state = _state(tmp_path)
    hotspot = _FakeHotspot()
    window = _overlay_with_fakes(monkeypatch, state, hotspot)
    monkeypatch.setattr(overlay, "is_desktop_foreground", lambda: True)

    window._tick()
    state.article = SimpleNamespace(url="https://it.wikipedia.org/wiki/Altro")
    window._tick()

    assert len(hotspot.shown) == 6
    assert window._state_key == window._state_signature(state)
    window.close()
