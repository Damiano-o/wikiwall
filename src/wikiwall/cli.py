from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import __version__
from .config import load_config, save_default_config
from .core import WikiWall
from .history import History
from .paths import config_path, history_path, log_path
from .startup import StartupError, install_startup, uninstall_startup
from .template import THEMES
from .watcher import Watcher

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wikiwall",
        description="Una voce di qualità di Wikipedia italiano sul tuo desktop Windows.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log dettagliato",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    change = sub.add_parser("next", help="Cambia subito lo sfondo")
    change.add_argument("--theme", choices=sorted(THEMES), default=None)
    change.add_argument("--width", type=int, default=None, help="Larghezza in pixel")
    change.add_argument("--height", type=int, default=None, help="Altezza in pixel")
    change.add_argument("--output", type=Path, default=None, help="Percorso del PNG")
    change.add_argument(
        "--no-set",
        action="store_true",
        help="Genera l'immagine senza applicarla al desktop",
    )

    watch = sub.add_parser("watch", help="Aggiorna lo sfondo in background")
    watch.add_argument(
        "--no-tray",
        action="store_true",
        help="Avvia senza icona nella tray",
    )

    sub.add_parser("install", help="Avvia WikiWall automaticamente al login")
    sub.add_parser("uninstall", help="Rimuove l'avvio automatico")

    config = sub.add_parser("config", help="Mostra il file di configurazione")
    config.add_argument("--open", action="store_true", help="Apri il file in Notepad")

    history = sub.add_parser("history", help="Mostra le ultime voci usate")
    history.add_argument("--clear", action="store_true", help="Svuota lo storico")

    sub.add_parser("setup", help="Installa Chromium per Playwright")
    return parser


def _configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except Exception:  # noqa: BLE001 - console quirks must never crash the app
                pass


def configure_logging(verbose: bool = False) -> None:
    handlers: list[logging.Handler] = []
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    try:
        handlers.append(
            RotatingFileHandler(
                log_path(),
                maxBytes=1_000_000,
                backupCount=2,
                encoding="utf-8",
            )
        )
    except OSError:
        pass
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        handlers=handlers,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )


def cmd_next(args: argparse.Namespace) -> int:
    app = WikiWall(load_config())
    result = app.change(
        theme=args.theme,
        width=args.width,
        height=args.height,
        output=args.output,
        apply=not args.no_set,
    )
    label = "in vetrina" if result.article.quality == "vetrina" else "di qualità"
    print(f"Voce {label}: {result.article.title}")
    print(f"Immagine: {result.image_path}")
    if args.no_set:
        print("Sfondo non modificato (--no-set).")
    else:
        print("Sfondo aggiornato.")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    watcher = Watcher(WikiWall(load_config()))
    try:
        watcher.run(with_tray=not args.no_tray)
    except KeyboardInterrupt:
        watcher.stop()
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    try:
        destination = install_startup()
    except (OSError, StartupError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1
    print(f"Avvio automatico installato: {destination}")
    print("WikiWall partirà al prossimo accesso. Per avviarlo ora: wikiwall watch")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    try:
        removed = uninstall_startup()
    except (OSError, StartupError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1
    print("Avvio automatico rimosso." if removed else "Avvio automatico non presente.")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    path = config_path()
    if not path.exists():
        save_default_config(path)
    if args.open:
        opener = getattr(os, "startfile", None)
        if opener is not None:
            opener(path)
        else:
            webbrowser.open(path.as_uri())
        return 0
    print(f"File di configurazione: {path}\n")
    print(path.read_text(encoding="utf-8"))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    config = load_config()
    history = History(history_path(), config.history_size)
    if args.clear:
        history.clear()
        print("Storico svuotato.")
        return 0

    titles = list(reversed(history.recent()))
    if not titles:
        print("Lo storico è vuoto.")
        return 0
    for index, title in enumerate(titles, 1):
        print(f"{index:2d}. {title}")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    print("Installo Chromium per Playwright...")
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=False,
    )
    if result.returncode != 0:
        print("Installazione non riuscita.", file=sys.stderr)
        return result.returncode or 1
    print("Chromium pronto. Esegui: wikiwall next")
    return 0


COMMANDS = {
    "next": cmd_next,
    "watch": cmd_watch,
    "install": cmd_install,
    "uninstall": cmd_uninstall,
    "config": cmd_config,
    "history": cmd_history,
    "setup": cmd_setup,
}


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    try:
        return COMMANDS[args.command](args)
    except (RuntimeError, OSError) as exc:
        LOGGER.debug("Dettaglio dell'errore", exc_info=True)
        print(f"Errore: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrotto.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
