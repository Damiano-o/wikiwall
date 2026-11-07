from types import SimpleNamespace

from wikiwall.tray import OFF_TITLE, ON_TITLE, _icon_image, apply_state


def test_icon_looks_different_when_switched_off():
    on = _icon_image(True)
    off = _icon_image(False)
    assert on.size == off.size
    assert on.tobytes() != off.tobytes()


def test_apply_state_mirrors_the_switch_on_the_icon():
    icon = SimpleNamespace(icon=None, title=None)

    apply_state(icon, SimpleNamespace(enabled=False))
    assert icon.title == OFF_TITLE
    assert icon.icon is not None

    apply_state(icon, SimpleNamespace(enabled=True))
    assert icon.title == ON_TITLE


def test_apply_state_never_raises_on_a_broken_tray():
    class Broken:
        @property
        def icon(self):
            return None

        @icon.setter
        def icon(self, value):
            raise RuntimeError("tray chiusa")

    apply_state(Broken(), SimpleNamespace(enabled=True))
