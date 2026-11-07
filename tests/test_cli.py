import pytest

from wikiwall.cli import build_parser, main


def test_parser_next_options():
    args = build_parser().parse_args(
        [
            "next",
            "--no-set",
            "--theme",
            "dark",
            "--width",
            "800",
            "--height",
            "600",
        ]
    )
    assert args.command == "next"
    assert args.no_set is True
    assert args.theme == "dark"
    assert args.width == 800
    assert args.height == 600


def test_parser_watch_options():
    args = build_parser().parse_args(["watch", "--no-tray", "--no-overlay"])
    assert args.command == "watch"
    assert args.no_tray is True
    assert args.no_overlay is True


def test_parser_requires_a_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_config_creates_and_prints(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    assert main(["config"]) == 0
    output = capsys.readouterr().out
    assert "File di configurazione" in output
    assert "theme" in output
    assert (tmp_path / "config.toml").exists()


def test_history_empty(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    assert main(["history"]) == 0
    assert "vuoto" in capsys.readouterr().out


def test_install_and_uninstall_startup(monkeypatch, tmp_path, capsys):
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path / "home"))

    assert main(["install"]) == 0
    destination = (
        appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "WikiWall.vbs"
    )
    assert destination.exists()
    assert "installato" in capsys.readouterr().out

    assert main(["uninstall"]) == 0
    assert not destination.exists()
    assert "rimosso" in capsys.readouterr().out


def test_history_shows_titles(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    from wikiwall.history import History

    History(tmp_path / "history.json").add("Italia")

    assert main(["history"]) == 0
    assert "Italia" in capsys.readouterr().out


def test_config_open_is_best_effort(monkeypatch, tmp_path):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    opened = []
    monkeypatch.setattr("wikiwall.cli.webbrowser.open", lambda url: opened.append(url))
    monkeypatch.setattr(
        "wikiwall.cli.os.startfile",
        lambda path: opened.append(path),
        raising=False,
    )
    assert main(["config", "--open"]) == 0
    assert len(opened) == 1
    assert str(tmp_path / "config.toml") in str(opened[0])


def test_theme_parser_accepts_the_known_themes():
    assert build_parser().parse_args(["theme"]).name is None
    assert build_parser().parse_args(["theme", "dark"]).name == "dark"
    assert build_parser().parse_args(["theme", "dark", "--apply"]).apply is True


def test_theme_parser_rejects_unknown_themes():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["theme", "neon"])


def test_theme_command_shows_the_current_theme(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))

    assert main(["theme"]) == 0

    output = capsys.readouterr().out
    assert "Tema attuale: paper" in output
    assert "dark" in output


def test_theme_command_saves_the_choice(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))

    assert main(["theme", "dark"]) == 0

    text = (tmp_path / "config.toml").read_text(encoding="utf-8")
    assert 'theme = "dark"' in text
    assert "Tema impostato: dark" in capsys.readouterr().out


def test_watch_refuses_a_second_instance(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))

    class FakeLock:
        def acquire(self):
            return False

        def release(self):
            raise AssertionError("non deve rilasciare un lock mai preso")

    class BoomWatcher:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("il secondo watcher non deve partire")

    monkeypatch.setattr("wikiwall.cli.InstanceLock", FakeLock)
    monkeypatch.setattr("wikiwall.cli.Watcher", BoomWatcher)

    assert main(["watch"]) == 0
    assert "già in esecuzione" in capsys.readouterr().out


def test_off_persists_state(monkeypatch, tmp_path, capsys):
    from wikiwall.state import load_state, state_path

    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    assert main(["off"]) == 0
    assert "spento" in capsys.readouterr().out
    assert load_state(state_path()).enabled is False


def test_status_reflects_state(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    assert main(["off"]) == 0
    capsys.readouterr()
    assert main(["status"]) == 0
    output = capsys.readouterr().out
    assert "WikiWall: spento" in output
    assert "Watcher:" in output


def test_on_after_off_and_toggle(monkeypatch, tmp_path, capsys):
    from wikiwall.state import load_state, state_path

    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    assert main(["off"]) == 0
    assert main(["on"]) == 0
    assert load_state(state_path()).enabled is True
    assert main(["toggle"]) == 0
    assert load_state(state_path()).enabled is False


def test_on_when_already_on(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    assert main(["on"]) == 0
    assert "già acceso" in capsys.readouterr().out


def test_parser_switch_commands():
    for command in ("on", "off", "toggle", "status"):
        assert build_parser().parse_args([command]).command == command
