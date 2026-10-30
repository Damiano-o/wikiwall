from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .config import Config, load_config
from .history import History
from .paths import history_path, wallpaper_path
from .render import render_article
from .wallpaper import get_screen_size, set_wallpaper
from .wikipedia import Article, WikipediaClient, WikipediaError

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChangeResult:
    article: Article
    image_path: Path
    width: int
    height: int


class WikiWall:
    """Coordinate article selection, rendering, history and wallpaper setting."""

    def __init__(
        self,
        config: Config | None = None,
        client: WikipediaClient | None = None,
        history: History | None = None,
    ) -> None:
        self.config = config or load_config()
        self.client = client or WikipediaClient(cache_days=self.config.quality_cache_days)
        self.history = history or History(history_path(), self.config.history_size)

    def change(
        self,
        *,
        theme: str | None = None,
        width: int | None = None,
        height: int | None = None,
        output: Path | str | None = None,
        apply: bool = True,
    ) -> ChangeResult:
        theme = theme or self.config.theme
        if width is None or height is None:
            screen_width, screen_height = get_screen_size()
            width = width or self.config.width or screen_width
            height = height or self.config.height or screen_height

        try:
            article = self.client.random_article(recent=self.history.recent())
        except WikipediaError as exc:
            article = self.client.load_last()
            if article is None:
                raise
            LOGGER.warning("Wikipedia non raggiungibile, riuso l'ultima voce: %s", exc)

        self.client.save_last(article)
        destination = Path(output) if output is not None else wallpaper_path()
        image_path = render_article(article, destination, width, height, theme)

        if apply:
            set_wallpaper(image_path)
            self.history.add(article.title)

        return ChangeResult(
            article=article,
            image_path=image_path,
            width=width,
            height=height,
        )


__all__ = ["ChangeResult", "WikiWall"]
