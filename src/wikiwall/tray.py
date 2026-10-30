from __future__ import annotations

import logging
import webbrowser
from typing import Any

LOGGER = logging.getLogger(__name__)


def _icon_image() -> Any:
    from PIL import Image, ImageDraw, ImageFont

    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (2, 2, size - 3, size - 3),
        radius=14,
        fill=(243, 237, 226, 255),
        outline=(25, 23, 20, 255),
        width=2,
    )
    draw.rectangle((2, 2, 7, size - 3), fill=(151, 3, 2, 255))

    font = None
    for name in ("georgiab.ttf", "georgia.ttf", "timesbd.ttf", "segoeuib.ttf"):
        try:
            font = ImageFont.truetype(name, 38)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    draw.text((37, 33), "W", font=font, fill=(25, 23, 20, 255), anchor="mm")
    return image


def create_icon(watcher: Any) -> Any:
    """Build the pystray icon. Imported lazily so headless use never needs a tray."""
    import pystray
    from pystray import Menu, MenuItem

    def open_article(icon: Any, item: Any) -> None:
        try:
            webbrowser.open(watcher.current_url)
        except Exception:  # noqa: BLE001 - opening a browser is best effort
            LOGGER.exception("Impossibile aprire la voce nel browser")

    icon = pystray.Icon(
        "wikiwall",
        _icon_image(),
        "WikiWall",
        menu=Menu(
            MenuItem(
                "Cambia ora",
                lambda icon, item: watcher.request_change(),
                default=True,
            ),
            MenuItem(
                "Salta voce",
                lambda icon, item: watcher.skip_async(),
            ),
            MenuItem("Apri voce", open_article),
            MenuItem(
                "QR e link cliccabili",
                lambda icon, item: watcher.toggle_clickable_qr(),
                checked=lambda item: watcher.clickable_qr,
            ),
            MenuItem(
                "Pausa",
                lambda icon, item: watcher.toggle_pause(),
                checked=lambda item: watcher.paused,
            ),
            Menu.SEPARATOR,
            MenuItem("Esci", lambda icon, item: watcher.stop()),
        ),
    )
    return icon


__all__ = ["create_icon"]
