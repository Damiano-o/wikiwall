from wikiwall.hotkey import HotkeyListener


def test_stopping_a_listener_that_never_started_is_safe():
    listener = HotkeyListener(lambda: None)
    listener.stop()
    assert listener.running is False
