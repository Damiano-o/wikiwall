from __future__ import annotations

import json
from pathlib import Path

from .paths import atomic_write_text


class History:
    """A small, crash-safe list of recently shown article titles."""

    def __init__(self, path: Path, limit: int = 50) -> None:
        self.path = path
        self.limit = max(1, limit)

    def _load(self) -> list[str]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, str)]

    def recent(self) -> list[str]:
        return self._load()[-self.limit :]

    def add(self, title: str) -> None:
        items = [item for item in self._load() if item != title]
        items.append(title)
        items = items[-self.limit :]
        atomic_write_text(self.path, json.dumps(items, ensure_ascii=False, indent=2))

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


__all__ = ["History"]
