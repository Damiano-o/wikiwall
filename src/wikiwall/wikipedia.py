from __future__ import annotations

import json
import logging
import random
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import requests

from .paths import atomic_write_text
from .paths import cache_dir as default_cache_dir

LOGGER = logging.getLogger(__name__)

USER_AGENT = (
    "WikiWall/0.1 (https://github.com/Damiano-o/wikiwall; "
    "contact: Damiano-o@users.noreply.github.com)"
)

QUALITY_SOURCES: tuple[tuple[str, str], ...] = (
    ("vetrina", "Wikipedia:Vetrina"),
    ("qualità", "Wikipedia:Voci di qualità"),
)

VETRINA_SHARE = 0.65
MIN_QUALITY_TITLES = 100


class WikipediaError(RuntimeError):
    """Raised when Wikipedia cannot be queried."""


class ArticleNotFound(WikipediaError):
    """Raised when an article has no usable summary."""


@dataclass(frozen=True, slots=True)
class Article:
    title: str
    description: str
    extract: str
    url: str
    image_url: str | None
    quality: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Article:
        return cls(
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            extract=str(data.get("extract", "")),
            url=str(data.get("url", "")),
            image_url=data.get("image_url"),
            quality=str(data.get("quality", "")),
        )


def _retry_after(response: Any, default: float = 5.0) -> float:
    try:
        return max(0.0, float(response.headers.get("Retry-After", default)))
    except (TypeError, ValueError):
        return default


class WikipediaClient:
    """Fetch quality article lists and summaries from a Wikipedia edition."""

    def __init__(
        self,
        language: str = "it",
        cache_dir: Path | None = None,
        timeout: float = 30.0,
        cache_days: int = 7,
        session: Any | None = None,
    ) -> None:
        self.language = language
        self.timeout = timeout
        self.cache_days = max(1, cache_days)
        self.api_url = f"https://{language}.wikipedia.org/w/api.php"
        self.cache_path = (cache_dir or default_cache_dir()) / "quality.json"
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------ quality list

    def quality_titles(self, refresh: bool = False) -> list[tuple[str, str]]:
        cached = self._load_cache()
        if cached is not None and not refresh and self._is_fresh(cached[0]):
            return cached[1]

        try:
            items = self._fetch_quality_index()
            self._write_cache(items)
            return items
        except Exception as exc:  # noqa: BLE001 - fall back to a stale cache on any network issue
            if cached is not None:
                LOGGER.warning("Lista di qualità non aggiornata, uso la cache: %s", exc)
                return cached[1]
            raise WikipediaError(
                f"Impossibile scaricare la lista delle voci di qualità: {exc}"
            ) from exc

    def _fetch_quality_index(self) -> list[tuple[str, str]]:
        titles: dict[str, str] = {}
        for label, page in QUALITY_SOURCES:
            data = self._api_get(
                {
                    "action": "parse",
                    "page": page,
                    "prop": "links",
                    "format": "json",
                    "formatversion": "2",
                    "maxlag": "5",
                }
            )
            parse = data.get("parse") or {}
            for link in parse.get("links") or []:
                title = str(link.get("title", "")).strip()
                if link.get("ns") != 0 or not title:
                    continue
                titles.setdefault(title, label)

        if len(titles) < MIN_QUALITY_TITLES:
            raise WikipediaError(f"Lista di qualità troppo corta ({len(titles)} voci)")
        return sorted(titles.items())

    def _api_get(self, params: dict[str, str]) -> dict[str, Any]:
        last_error: object = "errore sconosciuto"
        for attempt in range(3):
            try:
                response = self.session.get(self.api_url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(1 + attempt)
                continue

            if response.status_code == 429:
                last_error = "HTTP 429 (troppe richieste)"
                time.sleep(min(_retry_after(response), 30.0))
                continue

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                last_error = exc
                if 500 <= response.status_code < 600:
                    time.sleep(1 + attempt)
                    continue
                break

            try:
                return response.json()
            except ValueError as exc:
                last_error = exc
                break

        raise WikipediaError(f"Richiesta a Wikipedia fallita: {last_error}")

    def _load_cache(self) -> tuple[datetime, list[tuple[str, str]]] | None:
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
            fetched = datetime.fromisoformat(str(raw["fetched_at"]))
            items = raw["items"]
            if fetched.tzinfo is None:
                fetched = fetched.replace(tzinfo=UTC)
            clean = [
                (str(item[0]), str(item[1]))
                for item in items
                if isinstance(item, list) and len(item) == 2
            ]
            if not clean:
                return None
            return fetched, clean
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _is_fresh(self, fetched: datetime) -> bool:
        return datetime.now(UTC) - fetched < timedelta(days=self.cache_days)

    def _write_cache(self, items: list[tuple[str, str]]) -> None:
        payload = {
            "fetched_at": datetime.now(UTC).isoformat(),
            "items": [list(item) for item in items],
        }
        atomic_write_text(
            self.cache_path,
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

    # ------------------------------------------------------------------ article

    def random_article(
        self,
        recent: Sequence[str] = (),
        rng: random.Random | None = None,
    ) -> Article:
        rng = rng or random.Random()
        items = self.quality_titles()
        if not items:
            raise WikipediaError("Nessuna voce di qualità disponibile")

        recent_set = set(recent)
        candidates = [(title, label) for title, label in items if title not in recent_set]
        if not candidates:
            candidates = items

        vetrina = [title for title, label in candidates if label == "vetrina"]
        qualita = [title for title, label in candidates if label != "vetrina"]

        if vetrina and qualita:
            pool = vetrina if rng.random() < VETRINA_SHARE else qualita
        else:
            pool = vetrina or qualita

        labels = dict(candidates)
        last_error: object = "nessun candidato"
        for title in rng.sample(pool, min(5, len(pool))):
            try:
                article = self.summary(title, labels.get(title, ""))
            except WikipediaError as exc:
                last_error = exc
                LOGGER.warning("Voce %s non disponibile: %s", title, exc)
                continue
            if article.extract:
                return article

        raise WikipediaError(f"Nessuna voce recuperabile: {last_error}")

    def summary(self, title: str, quality: str = "") -> Article:
        data = self._api_get(
            {
                "action": "query",
                "prop": "extracts|pageimages|description|info",
                "exchars": "1400",
                "explaintext": "1",
                "piprop": "original|thumbnail",
                "inprop": "url",
                "redirects": "1",
                "titles": title,
                "format": "json",
                "formatversion": "2",
                "maxlag": "5",
            }
        )
        pages = (data.get("query") or {}).get("pages") or []
        if not pages:
            raise ArticleNotFound(f"Voce non trovata: {title}")

        page = pages[0]
        if page.get("missing") or page.get("invalid"):
            raise ArticleNotFound(f"Voce non trovata: {title}")

        extract = str(page.get("extract") or "").strip()
        if not extract:
            raise ArticleNotFound(f"Nessun estratto per {title}")

        original = page.get("original") or {}
        thumbnail = page.get("thumbnail") or {}
        image_url = original.get("source") or thumbnail.get("source") or None
        page_url = page.get("fullurl") or (
            f"https://{self.language}.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='/')}"
        )

        return Article(
            title=str(page.get("title") or title),
            description=str(page.get("description") or "").strip(),
            extract=extract,
            url=unquote(str(page_url)),
            image_url=str(image_url) if image_url else None,
            quality=quality,
        )

    # ------------------------------------------------------------------ offline fallback

    @property
    def last_article_path(self) -> Path:
        return self.cache_path.parent / "last_article.json"

    def save_last(self, article: Article) -> None:
        atomic_write_text(
            self.last_article_path,
            json.dumps(article.to_dict(), ensure_ascii=False, indent=2),
        )

    def load_last(self) -> Article | None:
        try:
            data = json.loads(self.last_article_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        article = Article.from_dict(data)
        return article if article.title and article.extract else None


__all__ = [
    "Article",
    "ArticleNotFound",
    "QUALITY_SOURCES",
    "WikipediaClient",
    "WikipediaError",
]
