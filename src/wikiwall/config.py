from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .paths import atomic_write_text, config_path

THEMES: tuple[str, ...] = ("paper", "dark")

DEFAULT_TOML = """\
[wikiwall]
language = "it"
theme = "paper"
interval_minutes = 10
idle_minutes = 5
desktop_cooldown_minutes = 10
history_size = 50
quality_cache_days = 7
clickable_qr = true
# width = 1920
# height = 1200
"""


@dataclass(frozen=True, slots=True)
class Config:
    language: str = "it"
    theme: str = "paper"
    interval_minutes: int = 10
    idle_minutes: int = 5
    desktop_cooldown_minutes: int = 10
    history_size: int = 50
    quality_cache_days: int = 7
    clickable_qr: bool = True
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


def _bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on", "si", "sì"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


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
        interval_minutes=_positive(section.get("interval_minutes"), 10),
        idle_minutes=_positive(section.get("idle_minutes"), 5),
        desktop_cooldown_minutes=_positive(section.get("desktop_cooldown_minutes"), 10),
        history_size=_positive(section.get("history_size"), 50),
        quality_cache_days=_positive(section.get("quality_cache_days"), 7),
        clickable_qr=_bool(section.get("clickable_qr"), True),
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


_THEME_KEY = re.compile(r"^\s*theme\s*=")
_SECTION = re.compile(r"^\s*\[")


def _section_bounds(lines: list[str]) -> tuple[int, int] | None:
    """Return the (start, end) line range of the [wikiwall] section."""
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "[wikiwall]":
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if _SECTION.match(lines[index]):
            end = index
            break
    return start + 1, end


def _replace_theme(lines: list[str], start: int, end: int, theme: str) -> bool:
    for index in range(start, end):
        if _THEME_KEY.match(lines[index]):
            prefix = lines[index].split("=", 1)[0].rstrip()
            lines[index] = f'{prefix} = "{theme}"'
            return True
    return False


def save_theme(theme: str, path: Path | None = None) -> Path:
    """Store *theme* in the config file, keeping comments and other keys."""
    name = theme.strip().lower()
    if name not in THEMES:
        raise ValueError(f"Tema sconosciuto: {theme}")

    target = path or config_path()
    if not target.exists():
        save_default_config(target)
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []

    bounds = _section_bounds(lines)
    if bounds is not None:
        start, end = bounds
        if not _replace_theme(lines, start, end, name):
            lines.insert(start, f'theme = "{name}"')
    else:
        top_end = next(
            (index for index, line in enumerate(lines) if _SECTION.match(line)),
            len(lines),
        )
        if not _replace_theme(lines, 0, top_end, name):
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend(["[wikiwall]", f'theme = "{name}"'])

    atomic_write_text(target, "\n".join(lines).rstrip() + "\n")
    return target


__all__ = [
    "Config",
    "DEFAULT_TOML",
    "THEMES",
    "load_config",
    "save_default_config",
    "save_theme",
]
