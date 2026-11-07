from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

from .core import ChangeResult, WikiWall
from .hotkey import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    TOGGLE_HOTKEY_ID,
    VK_O,
    HotkeyListener,
)
from .overlay import run_overlay
from .paths import state_path
from .state import State, load_state, save_state
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
        state_file: Path | None = None,
        enabled: bool = True,
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
        self.clickable_qr = config.clickable_qr

        self._stop = threading.Event()
        self._change_requested = threading.Event()
        self._change_lock = threading.Lock()
        self._overlay_stop = threading.Event()
        self._overlay_thread: threading.Thread | None = None
        self._hotkey: HotkeyListener | None = None
        self._enabled = enabled
        self._state_file = state_file
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
    def enabled(self) -> bool:
        """True while WikiWall is allowed to change the wallpaper."""
        return self._enabled

    @property
    def paused(self) -> bool:
        """Alias kept for older callers: paused is the same as switched off."""
        return not self._enabled

    @property
    def current_url(self) -> str:
        if self.current is not None:
            return self.current.article.url
        return "https://it.wikipedia.org"

    def request_change(self) -> None:
        """Ask the loop to change the wallpaper at the next tick."""
        self._change_requested.set()

    def skip_current(self) -> bool:
        """Change the wallpaper immediately, ignoring the normal cooldowns."""
        return self._change("salta")

    def skip_async(self) -> None:
        """Skip in a worker thread so tray and hotkey callbacks stay responsive."""
        threading.Thread(
            target=self.skip_current,
            name="wikiwall-skip",
            daemon=True,
        ).start()

    def toggle_pause(self) -> None:
        """Backwards-compatible alias for :meth:`toggle_enabled`."""
        self.toggle_enabled()

    def toggle_enabled(self) -> bool:
        """Switch WikiWall on or off and return the new state."""
        return self.set_enabled(not self._enabled)

    def toggle_enabled_async(self) -> None:
        """Toggle from a callback thread without blocking it."""
        threading.Thread(
            target=self.toggle_enabled,
            name="wikiwall-toggle",
            daemon=True,
        ).start()

    def set_enabled(self, enabled: bool, *, persist: bool = True) -> bool:
        """Turn the wallpaper rotation on or off, keeping the current image."""
        enabled = bool(enabled)
        changed = enabled != self._enabled
        self._enabled = enabled
        if enabled:
            self.last_idle = get_idle_seconds()
        else:
            self._change_requested.clear()
        if changed:
            LOGGER.info(
                "WikiWall %s: lo sfondo resta quello attuale",
                "acceso" if enabled else "spento",
            )
        if persist:
            self._save_state()
        self._refresh_tray()
        return enabled

    def _save_state(self) -> None:
        path = self._state_file
        if path is None:
            return
        try:
            save_state(State(enabled=self._enabled, updated=time.time()), path)
        except OSError:
            LOGGER.debug("Impossibile salvare lo stato in %s", path, exc_info=True)

    def _load_state(self) -> None:
        """Read the persisted switch before the loop starts."""
        path = self._state_file
        if path is None:
            return
        state = load_state(path)
        if state.enabled != self._enabled:
            self._enabled = state.enabled
            LOGGER.info("Stato salvato: WikiWall %s", state.describe())

    def _poll_state(self) -> None:
        """Apply an on/off choice made by another process (``wikiwall on|off``)."""
        path = self._state_file
        if path is None:
            return
        state = load_state(path)
        if state.enabled == self._enabled:
            return
        self._enabled = state.enabled
        if self._enabled:
            self.last_idle = get_idle_seconds()
        else:
            self._change_requested.clear()
        LOGGER.info("WikiWall %s (comando esterno)", state.describe())
        self._refresh_tray()

    def toggle_clickable_qr(self) -> None:
        self.clickable_qr = not self.clickable_qr
        LOGGER.info("QR e link cliccabili: %s", "sì" if self.clickable_qr else "no")
        self._refresh_tray()

    def _refresh_tray(self) -> None:
        if self._tray is None:
            return
        try:
            from .tray import apply_state

            apply_state(self._tray, self)
            self._tray.update_menu()
        except Exception:  # noqa: BLE001 - the tray is optional
            LOGGER.debug("Impossibile aggiornare il menu della tray", exc_info=True)

    def start_interaction(self, *, with_overlay: bool = True) -> None:
        """Start the clickable overlay and the global Ctrl+Alt+N shortcut."""
        if with_overlay:
            try:
                self._overlay_stop.clear()
                self._overlay_thread = threading.Thread(
                    target=run_overlay,
                    args=(self, self._overlay_stop),
                    name="wikiwall-overlay",
                    daemon=True,
                )
                self._overlay_thread.start()
                LOGGER.info("Overlay cliccabile avviato")
            except Exception:  # noqa: BLE001 - overlay is an enhancement
                LOGGER.exception("Overlay cliccabile non disponibile")
                self._overlay_thread = None

        try:
            self._hotkey = HotkeyListener(self.skip_async)
            self._hotkey.add(
                TOGGLE_HOTKEY_ID,
                MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
                VK_O,
                self.toggle_enabled_async,
            )
            self._hotkey.start()
        except Exception:  # noqa: BLE001 - the tray and the pill still work
            LOGGER.exception("Scorciatoia globale non disponibile")
            self._hotkey = None

    def stop_interaction(self) -> None:
        """Stop the overlay thread and unregister the global shortcut."""
        self._overlay_stop.set()
        thread = self._overlay_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._overlay_thread = None

        hotkey = self._hotkey
        if hotkey is not None:
            try:
                hotkey.stop()
            except Exception:  # noqa: BLE001 - shutdown is best effort
                LOGGER.debug("Errore fermando la scorciatoia globale", exc_info=True)
            self._hotkey = None

    def stop(self) -> None:
        self._stop.set()
        self._overlay_stop.set()

    # ------------------------------------------------------------------ decision logic

    def should_change(self, now: float, idle: float, desktop: bool) -> str | None:
        """Return a trigger name when the wallpaper should change now."""
        if not self._enabled:
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
        with self._change_lock:
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

    def run(self, with_tray: bool = True, with_overlay: bool = True) -> None:
        # The turn-off choice must win over a restart: read it before the tray,
        # so the icon is already grey when WikiWall starts switched off.
        if self._state_file is None:
            self._state_file = state_path()
        if self._state_file.exists():
            self._load_state()
        else:
            self._save_state()

        if with_tray:
            try:
                from .tray import create_icon

                self._tray = create_icon(self)
                self._tray.run_detached()
                LOGGER.info("Icona nella tray avviata")
            except Exception:  # noqa: BLE001 - the watcher still works without a tray
                LOGGER.exception("Tray non disponibile, continuo senza icona")
                self._tray = None

        self.start_interaction(with_overlay=with_overlay)
        self.last_change = time.monotonic() - self.interval_seconds - 1
        self.last_idle = get_idle_seconds()
        LOGGER.info(
            "Watcher avviato: intervallo %.0f min, soglia inattività %.0f min, %s",
            self.interval_seconds / 60,
            self.idle_threshold_seconds / 60,
            "acceso" if self._enabled else "spento",
        )

        try:
            while not self._stop.is_set():
                self._poll_state()
                now = time.monotonic()
                idle = get_idle_seconds()
                desktop = is_desktop_foreground()

                if self._change_requested.is_set():
                    self._change_requested.clear()
                    self.last_idle = idle
                    reason: str | None = "manuale" if self._enabled else None
                    if reason is None:
                        LOGGER.info("Cambio ignorato: WikiWall è spento")
                else:
                    reason = self.should_change(now, idle, desktop)

                if reason is not None:
                    self._change(reason)

                self._stop.wait(self.tick_seconds)
        finally:
            self.stop_interaction()
            if self._tray is not None:
                try:
                    self._tray.stop()
                except Exception:  # noqa: BLE001 - shutdown is best effort
                    LOGGER.debug("Errore fermando la tray", exc_info=True)
                self._tray = None
            LOGGER.info("Watcher fermato")


__all__ = ["Watcher"]
