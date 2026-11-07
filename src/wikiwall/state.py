"""Persisted on/off switch shared by the CLI, the tray and the watcher.

The state lives in ``state.json`` inside the WikiWall data directory, so the
last choice survives a reboot: if you switch WikiWall off, it stays off until
you switch it back on, and your current wallpaper is left alone.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from .paths import atomic_write_text, state_path

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class State:
    """Whether the watcher may change the wallpaper, plus when it was set."""

    enabled: bool = True
    updated: float = 0.0

    def describe(self) -> str:
        return "acceso" if self.enabled else "spento"


def _resolve(path: Path | str | None) -> Path:
    return Path(path) if path is not None else state_path()


def load_state(path: Path | str | None = None) -> State:
    """Read the saved state; anything unreadable falls back to enabled."""
    target = _resolve(path)
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return State()
    except OSError:
        LOGGER.debug("Impossibile leggere %s", target, exc_info=True)
        return State()

    try:
        data = json.loads(raw)
    except ValueError:
        LOGGER.warning("Stato illeggibile in %s: uso il valore predefinito", target)
        return State()
    if not isinstance(data, dict):
        return State()

    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        enabled = True
    updated = data.get("updated")
    if not isinstance(updated, (int, float)):
        updated = 0.0
    return State(enabled=enabled, updated=float(updated))


def save_state(state: State, path: Path | str | None = None) -> Path:
    """Write *state* atomically so a crash never leaves a half file behind."""
    target = _resolve(path)
    payload = {
        "enabled": bool(state.enabled),
        "updated": round(float(state.updated or time.time()), 3),
    }
    atomic_write_text(target, json.dumps(payload, indent=2) + "\n")
    return target


def set_enabled(enabled: bool, path: Path | str | None = None) -> Path:
    """Persist the on/off choice and return where it was written."""
    return save_state(State(enabled=bool(enabled), updated=time.time()), path)


__all__ = ["State", "load_state", "save_state", "set_enabled"]
