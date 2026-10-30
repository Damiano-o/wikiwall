from __future__ import annotations

import os
import tempfile
from pathlib import Path

APP_NAME = "WikiWall"


def _base_dir() -> Path:
    override = os.environ.get("WIKIWALL_HOME")
    if override:
        return Path(override).expanduser()
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / APP_NAME
    return Path.home() / ".wikiwall"


def app_dir() -> Path:
    path = _base_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = app_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return app_dir() / "config.toml"


def history_path() -> Path:
    return app_dir() / "history.json"


def wallpaper_path() -> Path:
    return app_dir() / "wallpaper.png"


def log_path() -> Path:
    return app_dir() / "wikiwall.log"


def last_article_path() -> Path:
    return cache_dir() / "last_article.json"


def quality_cache_path() -> Path:
    return cache_dir() / "quality.json"


def atomic_write_text(path: Path, text: str) -> None:
    """Write text to *path* atomically, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
