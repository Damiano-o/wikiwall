"""Keep a single watcher alive, so two overlays never fight over the desktop."""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO

from .paths import lock_path


class InstanceLock:
    """An advisory, crash-safe lock file for the background watcher.

    Windows releases ``msvcrt.locking`` locks when the process dies, so a stale
    lock file never blocks the next start.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or lock_path()
        self._handle: IO[str] | None = None

    @property
    def held(self) -> bool:
        return self._handle is not None

    def acquire(self) -> bool:
        """Return True when this process now owns the lock."""
        if self._handle is not None:
            return True

        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        try:
            self._lock(handle)
        except OSError:
            handle.close()
            return False

        self._handle = handle
        try:
            handle.seek(0)
            handle.truncate()
            handle.write(f"{os.getpid()}\n")
            handle.flush()
        except OSError:  # pragma: no cover - diagnostics only
            pass
        return True

    def release(self) -> None:
        handle = self._handle
        if handle is None:
            return
        self._handle = None
        try:
            self._unlock(handle)
        except OSError:  # pragma: no cover - best effort on shutdown
            pass
        finally:
            handle.close()

    def __enter__(self) -> InstanceLock:
        if not self.acquire():
            raise RuntimeError("Un'altra istanza di WikiWall è già in esecuzione.")
        return self

    def __exit__(self, *_exc: object) -> None:
        self.release()

    @staticmethod
    def _lock(handle: IO[str]) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(handle: IO[str]) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = ["InstanceLock"]
