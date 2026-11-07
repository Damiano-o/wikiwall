import json

from wikiwall import state as state_module
from wikiwall.paths import state_path
from wikiwall.state import State, load_state, save_state, set_enabled


def test_missing_file_means_enabled(tmp_path):
    assert load_state(tmp_path / "state.json") == State()


def test_roundtrip(tmp_path):
    target = tmp_path / "state.json"
    save_state(State(enabled=False, updated=1234.5), target)
    loaded = load_state(target)
    assert loaded.enabled is False
    assert loaded.updated == 1234.5


def test_set_enabled_writes_timestamp(tmp_path):
    target = tmp_path / "state.json"
    set_enabled(False, target)
    loaded = load_state(target)
    assert loaded.enabled is False
    assert loaded.updated > 0


def test_corrupt_file_falls_back_to_enabled(tmp_path):
    target = tmp_path / "state.json"
    target.write_text("{non json", encoding="utf-8")
    assert load_state(target).enabled is True


def test_unexpected_payload_types_are_ignored(tmp_path):
    target = tmp_path / "state.json"
    target.write_text(json.dumps({"enabled": "no", "updated": "ieri"}), encoding="utf-8")
    loaded = load_state(target)
    assert loaded.enabled is True
    assert loaded.updated == 0.0


def test_non_dict_payload_falls_back(tmp_path):
    target = tmp_path / "state.json"
    target.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert load_state(target).enabled is True


def test_state_path_follows_wikiwall_home(monkeypatch, tmp_path):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    assert state_path() == tmp_path / "state.json"


def test_describe():
    assert State(enabled=True).describe() == "acceso"
    assert State(enabled=False).describe() == "spento"


def test_save_state_is_atomic(monkeypatch, tmp_path):
    target = tmp_path / "state.json"
    set_enabled(True, target)
    set_enabled(False, target)
    assert load_state(target).enabled is False
    leftovers = [item for item in tmp_path.iterdir() if item.name != "state.json"]
    assert leftovers == []


def test_default_state_path_uses_app_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    monkeypatch.setattr(state_module, "state_path", state_path)
    set_enabled(False)
    assert json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))["enabled"] is False
