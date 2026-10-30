from wikiwall.config import Config, load_config


def test_default_config_is_created(tmp_path, monkeypatch):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    cfg = load_config()
    assert cfg == Config()
    assert (tmp_path / "config.toml").exists()


def test_custom_config_is_loaded(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[wikiwall]\ntheme = "dark"\ninterval_minutes = 15\nwidth = 2560\n',
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.theme == "dark"
    assert cfg.interval_minutes == 15
    assert cfg.width == 2560
    assert cfg.height is None


def test_invalid_values_fall_back(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[wikiwall]\ntheme = "neon"\ninterval_minutes = -1\nhistory_size = "tanti"\n',
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.theme == "paper"
    assert cfg.interval_minutes == 60
    assert cfg.history_size == 50
