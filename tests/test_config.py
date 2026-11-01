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


def test_clickable_qr_defaults_to_true(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[wikiwall]\n", encoding="utf-8")
    assert load_config(path).clickable_qr is True


def test_clickable_qr_can_be_disabled(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[wikiwall]\nclickable_qr = false\n", encoding="utf-8")
    assert load_config(path).clickable_qr is False


def test_invalid_values_fall_back(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[wikiwall]\ntheme = "neon"\ninterval_minutes = -1\nhistory_size = "tanti"\n',
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.theme == "paper"
    assert cfg.interval_minutes == 10
    assert cfg.history_size == 50


def test_save_theme_replaces_the_value_and_keeps_comments(tmp_path):
    from wikiwall.config import save_theme

    path = tmp_path / "config.toml"
    path.write_text(
        '[wikiwall]\n# tema preferito\ntheme = "paper"\ninterval_minutes = 5\n',
        encoding="utf-8",
    )

    save_theme("dark", path)

    text = path.read_text(encoding="utf-8")
    assert 'theme = "dark"' in text
    assert "# tema preferito" in text
    assert "interval_minutes = 5" in text
    assert load_config(path).theme == "dark"


def test_save_theme_adds_the_key_inside_the_section(tmp_path):
    from wikiwall.config import save_theme

    path = tmp_path / "config.toml"
    path.write_text("[wikiwall]\ninterval_minutes = 5\n", encoding="utf-8")

    save_theme("dark", path)

    assert load_config(path).theme == "dark"
    assert load_config(path).interval_minutes == 5


def test_save_theme_creates_the_section_when_missing(tmp_path):
    from wikiwall.config import save_theme

    path = tmp_path / "config.toml"
    path.write_text('language = "it"\n', encoding="utf-8")

    save_theme("dark", path)

    text = path.read_text(encoding="utf-8")
    assert "[wikiwall]" in text
    assert 'language = "it"' in text
    assert load_config(path).theme == "dark"


def test_save_theme_rejects_unknown_themes(tmp_path):
    import pytest

    from wikiwall.config import save_theme

    with pytest.raises(ValueError):
        save_theme("neon", tmp_path / "config.toml")
