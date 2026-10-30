from pathlib import Path

import pytest

from wikiwall import wallpaper


def test_screen_size_is_positive_on_windows():
    width, height = wallpaper.get_screen_size()
    assert width > 0
    assert height > 0


def test_screen_size_falls_back_off_windows(monkeypatch):
    monkeypatch.setattr(wallpaper, "IS_WINDOWS", False)
    assert wallpaper.get_screen_size((1280, 720)) == (1280, 720)


def test_set_wallpaper_rejects_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(wallpaper, "IS_WINDOWS", True)
    with pytest.raises(wallpaper.WallpaperError):
        wallpaper.set_wallpaper(tmp_path / "manca.png")


def test_set_wallpaper_reports_non_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(wallpaper, "IS_WINDOWS", False)
    image = tmp_path / "sfondo.png"
    image.write_bytes(b"not really a png")
    with pytest.raises(wallpaper.WallpaperError, match="Windows"):
        wallpaper.set_wallpaper(image)


def test_set_wallpaper_calls_native_api(monkeypatch, tmp_path):
    image = tmp_path / "sfondo.png"
    image.write_bytes(b"not really a png")
    seen: list[Path] = []
    monkeypatch.setattr(wallpaper, "IS_WINDOWS", True)
    monkeypatch.setattr(wallpaper, "_set_wallpaper_fill", lambda: None)
    monkeypatch.setattr(
        wallpaper,
        "_set_wallpaper_native",
        lambda path: seen.append(path) or True,
    )
    wallpaper.set_wallpaper(image)
    assert seen == [image.resolve()]


def test_set_wallpaper_raises_when_windows_refuses(monkeypatch, tmp_path):
    image = tmp_path / "sfondo.png"
    image.write_bytes(b"not really a png")
    monkeypatch.setattr(wallpaper, "IS_WINDOWS", True)
    monkeypatch.setattr(wallpaper, "_set_wallpaper_fill", lambda: None)
    monkeypatch.setattr(wallpaper, "_set_wallpaper_native", lambda path: False)
    with pytest.raises(wallpaper.WallpaperError, match="accettato"):
        wallpaper.set_wallpaper(image)


def test_idle_seconds_off_windows(monkeypatch):
    monkeypatch.setattr(wallpaper, "IS_WINDOWS", False)
    assert wallpaper.get_idle_seconds() == 0.0


def test_idle_seconds_on_windows_is_non_negative():
    assert wallpaper.get_idle_seconds() >= 0.0


def test_desktop_foreground_off_windows(monkeypatch):
    monkeypatch.setattr(wallpaper, "IS_WINDOWS", False)
    assert wallpaper.is_desktop_foreground() is False
