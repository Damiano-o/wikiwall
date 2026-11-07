from __future__ import annotations

import logging
import webbrowser
from typing import Any

LOGGER = logging.getLogger(__name__)

ON_TITLE = "WikiWall — attivo"
OFF_TITLE = "WikiWall — spento"


def _icon_image(enabled: bool = True) -> Any:
    from PIL import Image, ImageDraw, ImageFont

    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    paper = (243, 237, 226, 255) if enabled else (226, 224, 219, 255)
    ink = (25, 23, 20, 255) if enabled else (128, 126, 120, 255)
    accent = (151, 3, 2, 255) if enabled else (150, 148, 143, 255)

    draw.rounded_rectangle(
        (2, 2, size - 3, size - 3),
        radius=14,
        fill=paper,
        outline=ink,
        width=2,
    )
    draw.rectangle((2, 2, 7, size - 3), fill=accent)

    font = None
    for name in ("georgiab.ttf", "georgia.ttf", "timesbd.ttf", "segoeuib.ttf"):
        try:
            font = ImageFont.truetype(name, 38)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    draw.text((37, 33), "W", font=font, fill=ink, anchor="mm")
    if not enabled:
        # A small grey dot in the corner reads as "off" at 16 px too.
        draw.ellipse((size - 22, size - 22, size - 8, size - 8), fill=(150, 148, 143, 255))
    return image


def apply_state(icon: Any, watcher: Any) -> None:
    """Mirror the on/off switch on the tray icon and its tooltip."""
    try:
        icon.icon = _icon_image(bool(watcher.enabled))
        icon.title = ON_TITLE if watcher.enabled else OFF_TITLE
    except Exception:  # noqa: BLE001 - a tray hiccup must not break the watcher
        LOGGER.debug("Impossibile aggiornare l'icona della tray", exc_info=True)


def create_icon(watcher: Any) -> Any:
    """Build the pystray icon. Imported lazily so headless use never needs a tray."""
    import pystray
    from pystray import Menu, MenuItem

    def open_article(icon: Any, item: Any) -> None:
        try:
            webbrowser.open(watcher.current_url)
        except Exception:  # noqa: BLE001 - opening a browser is best effort
            LOGGER.exception("Impossibile aprire la voce nel browser")

    def toggle_label(item: Any) -> str:
        return "Spegni WikiWall" if watcher.enabled else "Accendi WikiWall"

    def is_on(item: Any) -> bool:
        return bool(watcher.enabled)

    menu = Menu(
        MenuItem(
            "Cambia ora",
            lambda icon, item: watcher.request_change(),
            enabled=is_on,
            default=True,
        ),
        MenuItem(
            "Salta voce",
            lambda icon, item: watcher.skip_async(),
            enabled=is_on,
        ),
        MenuItem("Apri voce", open_article),
        MenuItem(
            "QR e link cliccabili",
            lambda icon, item: watcher.toggle_clickable_qr(),
            checked=lambda item: watcher.clickable_qr,
        ),
        Menu.SEPARATOR,
        MenuItem(
            toggle_label,
            lambda icon, item: watcher.toggle_enabled(),
            checked=is_on,
        ),
        Menu.SEPARATOR,
        MenuItem("Esci", lambda icon, item: watcher.stop()),
    )

    icon = pystray.Icon(
        "wikiwall",
        _icon_image(bool(watcher.enabled)),
        ON_TITLE if watcher.enabled else OFF_TITLE,
        menu=menu,
    )
    return icon


__all__ = ["create_icon", "apply_state"]
