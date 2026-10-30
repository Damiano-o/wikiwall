import threading
from pathlib import Path

from wikiwall.config import Config
from wikiwall.core import ChangeResult
from wikiwall.watcher import Watcher
from wikiwall.wikipedia import Article

ARTICLE = Article(
    title="Italia",
    description="stato",
    extract="L'Italia è un paese.",
    url="https://it.wikipedia.org/wiki/Italia",
    image_url=None,
    quality="vetrina",
)


class FakeApp:
    config = Config()

    def __init__(self):
        self.calls = 0
        self.error = None

    def change(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ChangeResult(ARTICLE, Path("wallpaper.png"), 1920, 1080)


def make_watcher(app=None):
    return Watcher(
        app or FakeApp(),
        interval_minutes=60,
        idle_minutes=5,
        desktop_cooldown_minutes=10,
    )


def test_interval_trigger():
    watcher = make_watcher()
    watcher.last_change = 0.0
    assert watcher.should_change(3600.0, 0.0, False) == "intervallo"
    watcher.last_change = 3599.0
    assert watcher.should_change(3600.0, 0.0, False) is None


def test_idle_return_trigger():
    watcher = make_watcher()
    watcher.last_change = 0.0
    watcher.last_idle = 600.0
    assert watcher.should_change(1000.0, 0.0, False) == "ritorno"
    assert watcher.should_change(1001.0, 0.0, False) is None


def test_idle_return_requires_previous_idle():
    watcher = make_watcher()
    watcher.last_change = 0.0
    watcher.last_idle = 100.0
    assert watcher.should_change(1000.0, 0.0, False) is None


def test_desktop_trigger_after_hold():
    watcher = make_watcher()
    watcher.last_change = 0.0
    assert watcher.should_change(1000.0, 0.0, True) is None
    assert watcher.should_change(1002.0, 0.0, True) is None
    assert watcher.should_change(1004.0, 0.0, True) == "desktop"
    assert watcher.should_change(1005.0, 0.0, True) is None


def test_desktop_trigger_respects_cooldown():
    watcher = make_watcher()
    watcher.last_change = 900.0
    assert watcher.should_change(1000.0, 0.0, True) is None
    assert watcher.should_change(1004.0, 0.0, True) is None
    assert watcher.should_change(1501.0, 0.0, True) == "desktop"


def test_desktop_requires_a_new_entry():
    watcher = make_watcher()
    watcher.last_change = 0.0
    assert watcher.should_change(1000.0, 0.0, True) is None
    assert watcher.should_change(1004.0, 0.0, True) == "desktop"
    watcher.last_change = 1004.0
    assert watcher.should_change(1006.0, 0.0, True) is None
    assert watcher.should_change(1008.0, 0.0, False) is None
    assert watcher.should_change(1010.0, 0.0, True) is None
    assert watcher.should_change(1014.0, 0.0, True) is None


def test_pause_blocks_triggers(monkeypatch):
    monkeypatch.setattr("wikiwall.watcher.get_idle_seconds", lambda: 0.0)
    watcher = make_watcher()
    watcher.last_change = 0.0
    watcher.toggle_pause()
    assert watcher.paused is True
    assert watcher.should_change(3600.0, 0.0, False) is None
    watcher.toggle_pause()
    assert watcher.paused is False
    assert watcher.should_change(3600.0, 0.0, False) == "intervallo"


def test_change_updates_state_and_current_url():
    app = FakeApp()
    watcher = make_watcher(app)
    assert watcher.current_url == "https://it.wikipedia.org"
    assert watcher._change("manuale") is True
    assert app.calls == 1
    assert watcher.current is not None
    assert watcher.current_url == ARTICLE.url
    assert watcher.last_change > 0
    assert watcher.last_error is None


def test_skip_current_changes_immediately():
    app = FakeApp()
    watcher = make_watcher(app)
    assert watcher.skip_current() is True
    assert app.calls == 1
    assert watcher.current is not None
    assert watcher.current.article.title == "Italia"


def test_toggle_clickable_qr():
    watcher = make_watcher()
    assert watcher.clickable_qr is True
    watcher.toggle_clickable_qr()
    assert watcher.clickable_qr is False
    watcher.toggle_clickable_qr()
    assert watcher.clickable_qr is True


def test_change_records_error_without_crashing():
    app = FakeApp()
    app.error = RuntimeError("boom")
    watcher = make_watcher(app)
    assert watcher._change("intervallo") is False
    assert watcher.last_error == "boom"
    assert watcher.current is None


def test_request_change_sets_event():
    watcher = make_watcher()
    watcher.request_change()
    assert watcher._change_requested.is_set()
    watcher._change_requested.clear()
    assert not watcher._change_requested.is_set()


def test_stop_sets_event():
    watcher = make_watcher()
    watcher.stop()
    assert watcher._stop.is_set()


def test_start_and_stop_interaction(monkeypatch):
    overlay_started = threading.Event()
    overlay_stopped = threading.Event()

    class FakeHotkey:
        def __init__(self, callback):
            self.callback = callback
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True
            return True

        def stop(self):
            self.stopped = True

    def fake_overlay(watcher, stop_event):
        overlay_started.set()
        stop_event.wait(2)
        overlay_stopped.set()

    monkeypatch.setattr("wikiwall.watcher.run_overlay", fake_overlay)
    monkeypatch.setattr("wikiwall.watcher.HotkeyListener", FakeHotkey)

    watcher = make_watcher()
    watcher.start_interaction(with_overlay=True)
    assert overlay_started.wait(1)
    assert watcher._hotkey is not None
    hotkey = watcher._hotkey
    assert hotkey.started is True

    watcher.stop_interaction()
    assert overlay_stopped.wait(1)
    assert hotkey.stopped is True


def test_skip_async_runs_in_background(monkeypatch):
    watcher = make_watcher()
    called = threading.Event()
    monkeypatch.setattr(watcher, "skip_current", lambda: called.set())

    watcher.skip_async()

    assert called.wait(1)


def test_run_starts_and_stops_interaction(monkeypatch):
    watcher = make_watcher()
    events = []
    monkeypatch.setattr(
        watcher, "start_interaction", lambda **kwargs: events.append("start")
    )
    monkeypatch.setattr(watcher, "stop_interaction", lambda: events.append("stop"))
    monkeypatch.setattr("wikiwall.watcher.get_idle_seconds", lambda: 0.0)
    monkeypatch.setattr("wikiwall.watcher.is_desktop_foreground", lambda: False)
    monkeypatch.setattr(
        watcher, "_change", lambda reason: watcher._stop.set()
    )

    watcher.run(with_tray=False, with_overlay=False)

    assert events == ["start", "stop"]
