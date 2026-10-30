from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .paths import atomic_write_text, config_path

DEFAULT_TOML = """\
[wikiwall]
language = "it"
theme = "paper"
interval_minutes = 60
idle_minutes = 5
desktop_cooldown_minutes = 10
history_size = 50
quality_cache_days = 7
# width = 1920
# height = 1200
"""


@dataclass(frozen=True, slots=True)
class Config:
    language: str = "it"
    theme: str = "paper"
    interval_minutes: int = 60
    idle_minutes: int = 5
    desktop_cooldown_minutes: int = 10
    history_size: int = 50
    quality_cache_days: int = 7
    width: int | None = None
    height: int | None = None


def _positive(value: object, default: int) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _optional_positive(value: object) -> int | None:
    if value is None:
        return None
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _config_from_mapping(data: dict) -> Config:
    section = data.get("wikiwall", data)
    if not isinstance(section, dict):
        section = {}

    theme = str(section.get("theme", "paper")).strip().lower()
    if theme not in {"paper", "dark"}:
        theme = "paper"

    language = str(section.get("language", "it")).strip() or "it"
    return Config(
        language=language,
        theme=theme,
        interval_minutes=_positive(section.get("interval_minutes"), 60),
        idle_minutes=_positive(section.get("idle_minutes"), 5),
        desktop_cooldown_minutes=_positive(section.get("desktop_cooldown_minutes"), 10),
        history_size=_positive(section.get("history_size"), 50),
        quality_cache_days=_positive(section.get("quality_cache_days"), 7),
        width=_optional_positive(section.get("width")),
        height=_optional_positive(section.get("height")),
    )


def save_default_config(path: Path | None = None) -> Path:
    """Create the commented default config if it does not exist yet."""
    target = path or config_path()
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(target, DEFAULT_TOML)
    return target


def load_config(path: Path | None = None) -> Config:
    """Load configuration, creating a commented default file on first run."""
    target = path or config_path()
    if not target.exists():
        save_default_config(target)
    try:
        with target.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return Config()
    return _config_from_mapping(data)


__all__ = ["Config", "DEFAULT_TOML", "load_config", "save_default_config"]
