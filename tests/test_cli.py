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
    args = build_parser().parse_args(["watch", "--no-tray"])
    assert args.command == "watch"
    assert args.no_tray is True


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
