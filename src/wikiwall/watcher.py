from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .core import ChangeResult, WikiWall
from .wallpaper import get_idle_seconds, is_desktop_foreground

LOGGER = logging.getLogger(__name__)


class Watcher:
    """Background loop that refreshes the wallpaper at the right moments."""

    def __init__(
        self,
        app: WikiWall,
        *,
        interval_minutes: int | None = None,
        idle_minutes: int | None = None,
        desktop_cooldown_minutes: int | None = None,
        tick_seconds: float = 2.0,
        desktop_hold_seconds: float = 3.0,
        min_gap_seconds: float = 60.0,
    ) -> None:
        config = app.config
        self.app = app
        self.interval_seconds = float(
            (interval_minutes if interval_minutes is not None else config.interval_minutes) * 60
        )
        self.idle_threshold_seconds = float(
            (idle_minutes if idle_minutes is not None else config.idle_minutes) * 60
        )
        self.desktop_cooldown_seconds = float(
            (
                desktop_cooldown_minutes
                if desktop_cooldown_minutes is not None
                else config.desktop_cooldown_minutes
            )
            * 60
        )
        self.tick_seconds = tick_seconds
        self.desktop_hold_seconds = desktop_hold_seconds
        self.min_gap_seconds = min_gap_seconds

        self._stop = threading.Event()
        self._change_requested = threading.Event()
        self._paused = False
        self._desktop_was_foreground = False
        self._tray: Any | None = None

        self.last_change = 0.0
        self.last_idle = 0.0
        self.desktop_since: float | None = None
        self.desktop_triggered = False
        self.current: ChangeResult | None = None
        self.last_error: str | None = None

    # ------------------------------------------------------------------ public API

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def current_url(self) -> str:
        if self.current is not None:
            return self.current.article.url
        return "https://it.wikipedia.org"

    def request_change(self) -> None:
        """Ask the loop to change the wallpaper at the next tick."""
        self._change_requested.set()

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        if not self._paused:
            self.last_idle = get_idle_seconds()
        LOGGER.info("Watcher %s", "in pausa" if self._paused else "riattivato")

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------ decision logic

    def should_change(self, now: float, idle: float, desktop: bool) -> str | None:
        """Return a trigger name when the wallpaper should change now."""
        if self._paused:
            self.last_idle = idle
            return None

        reason: str | None = None
        if now - self.last_change >= self.interval_seconds:
            reason = "intervallo"
        elif (
            self.last_idle >= self.idle_threshold_seconds
            and idle <= 3.0
            and now - self.last_change >= self.min_gap_seconds
        ):
            reason = "ritorno"

        if desktop:
            if not self._desktop_was_foreground:
                self._desktop_was_foreground = True
                self.desktop_since = now
                self.desktop_triggered = False
            elif (
                not self.desktop_triggered
                and self.desktop_since is not None
                and now - self.desktop_since >= self.desktop_hold_seconds
                and now - self.last_change >= self.desktop_cooldown_seconds
            ):
                reason = reason or "desktop"
                self.desktop_triggered = True
        else:
            self._desktop_was_foreground = False
            self.desktop_since = None
            self.desktop_triggered = False

        self.last_idle = idle
        return reason

    # ------------------------------------------------------------------ loop

    def _change(self, reason: str) -> bool:
        try:
            result = self.app.change()
        except Exception as exc:  # noqa: BLE001 - a failed refresh must not kill the watcher
            LOGGER.exception("Cambio dello sfondo fallito (%s)", reason)
            self.last_error = str(exc)
            return False

        self.current = result
        self.last_change = time.monotonic()
        self.last_idle = 0.0
        self.desktop_triggered = True
        self.last_error = None
        LOGGER.info("Sfondo cambiato (%s): %s", reason, result.article.title)
        return True

    def run(self, with_tray: bool = True) -> None:
        if with_tray:
            try:
                from .tray import create_icon

                self._tray = create_icon(self)
                self._tray.run_detached()
                LOGGER.info("Icona nella tray avviata")
            except Exception:  # noqa: BLE001 - the watcher still works without a tray
                LOGGER.exception("Tray non disponibile, continuo senza icona")
                self._tray = None

        self.last_change = time.monotonic() - self.interval_seconds - 1
        self.last_idle = get_idle_seconds()
        LOGGER.info(
            "Watcher avviato: intervallo %.0f min, soglia inattività %.0f min",
            self.interval_seconds / 60,
            self.idle_threshold_seconds / 60,
        )

        try:
            while not self._stop.is_set():
                now = time.monotonic()
                idle = get_idle_seconds()
                desktop = is_desktop_foreground()

                if self._change_requested.is_set():
                    self._change_requested.clear()
                    self.last_idle = idle
                    reason: str | None = "manuale"
                else:
                    reason = self.should_change(now, idle, desktop)

                if reason is not None:
                    self._change(reason)

                self._stop.wait(self.tick_seconds)
        finally:
            if self._tray is not None:
                try:
                    self._tray.stop()
                except Exception:  # noqa: BLE001 - shutdown is best effort
                    LOGGER.debug("Errore fermando la tray", exc_info=True)
                self._tray = None
            LOGGER.info("Watcher fermato")


__all__ = ["Watcher"]
