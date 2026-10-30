from pathlib import Path

from wikiwall import startup


def test_startup_path_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    expected = (
        tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "WikiWall.vbs"
    )
    assert startup.startup_path() == expected


def test_install_and_uninstall_startup(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    python = tmp_path / "pythonw.exe"
    working_dir = tmp_path / "project"

    destination = startup.install_startup(python, working_dir)

    assert destination == startup.startup_path()
    content = destination.read_text(encoding="utf-16")
    assert str(python) in content
    assert "-m wikiwall watch" in content
    assert f'CurrentDirectory = "{working_dir}"' in content
    assert "shell.Run " in content

    assert startup.uninstall_startup() is True
    assert not destination.exists()
    assert startup.uninstall_startup() is False


def test_vbs_content_quotes_python_path(tmp_path):
    content = startup.vbs_content(Path(r"C:\Program Files\Python\pythonw.exe"), tmp_path)
    assert r"C:\Program Files\Python\pythonw.exe" in content
    assert "Chr(34)" in content
