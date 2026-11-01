from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
import requests

from wikiwall import wikipedia
from wikiwall.wikipedia import Article, WikipediaClient, WikipediaError


class FakeResponse:
    def __init__(self, payload=None, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        if not self.responses:
            raise AssertionError("richiesta inattesa")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_quality_titles_parses_links_and_dedupes(tmp_path, monkeypatch):
    monkeypatch.setattr(wikipedia, "MIN_QUALITY_TITLES", 1)
    session = FakeSession(
        [
            FakeResponse(
                {
                    "parse": {
                        "links": [
                            {"title": "Italia", "ns": 0},
                            {"title": "File:Map.png", "ns": 6},
                            {"title": "A", "ns": 0},
                            {"title": "Wikipedia:Policy", "ns": 4},
                        ]
                    }
                }
            ),
            FakeResponse(
                {
                    "parse": {
                        "links": [
                            {"title": "Italia", "ns": 0},
                            {"title": "B", "ns": 0},
                            {"title": "C", "ns": 0},
                        ]
                    }
                }
            ),
        ]
    )
    client = WikipediaClient(cache_dir=tmp_path, session=session)
    assert client.quality_titles() == [
        ("A", "vetrina"),
        ("B", "qualità"),
        ("C", "qualità"),
        ("Italia", "vetrina"),
    ]
    assert (tmp_path / "quality.json").exists()


def test_quality_titles_uses_fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(wikipedia, "MIN_QUALITY_TITLES", 1)
    quality = tmp_path / "quality.json"
    quality.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(UTC).isoformat(),
                "items": [["A", "vetrina"]],
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession([])
    client = WikipediaClient(cache_dir=tmp_path, session=session)
    assert client.quality_titles() == [("A", "vetrina")]
    assert session.calls == []


def test_quality_titles_falls_back_to_stale_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(wikipedia, "MIN_QUALITY_TITLES", 1)
    monkeypatch.setattr(wikipedia.time, "sleep", lambda _: None)
    quality = tmp_path / "quality.json"
    quality.write_text(
        json.dumps(
            {
                "fetched_at": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
                "items": [["A", "vetrina"]],
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession([requests.ConnectionError("offline")] * 3)
    client = WikipediaClient(cache_dir=tmp_path, session=session)
    assert client.quality_titles() == [("A", "vetrina")]


def test_api_get_retries_on_429(tmp_path, monkeypatch):
    monkeypatch.setattr(wikipedia.time, "sleep", lambda _: None)
    session = FakeSession(
        [
            FakeResponse({"ok": False}, status_code=429, headers={"Retry-After": "0"}),
            FakeResponse({"ok": True}),
        ]
    )
    client = WikipediaClient(cache_dir=tmp_path, session=session)
    assert client._api_get({"action": "query"}) == {"ok": True}


def test_summary_parses_api_payload(tmp_path):
    session = FakeSession(
        [
            FakeResponse(
                {
                    "query": {
                        "pages": [
                            {
                                "title": "La grande onda di Kanagawa",
                                "description": "xilografia di Katsushika Hokusai",
                                "extract": "La grande onda di Kanagawa è una xilografia.",
                                "original": {"source": "https://example.org/onda.jpg"},
                                "fullurl": (
                                    "https://it.wikipedia.org/wiki/La_grande_onda_di_Kanagawa"
                                ),
                            }
                        ]
                    }
                }
            )
        ]
    )
    client = WikipediaClient(cache_dir=tmp_path, session=session)
    article = client.summary("La grande onda di Kanagawa", "vetrina")
    assert article.title == "La grande onda di Kanagawa"
    assert article.description == "xilografia di Katsushika Hokusai"
    assert article.image_url == "https://example.org/onda.jpg"
    assert article.quality == "vetrina"
    assert article.url.endswith("La_grande_onda_di_Kanagawa")


def test_random_article_avoids_recent_titles(tmp_path, monkeypatch):
    monkeypatch.setattr(wikipedia, "MIN_QUALITY_TITLES", 1)
    quality = tmp_path / "quality.json"
    quality.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(UTC).isoformat(),
                "items": [["A", "vetrina"], ["B", "vetrina"], ["C", "vetrina"]],
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(
        [
            FakeResponse(
                {
                    "query": {
                        "pages": [
                            {
                                "title": "C",
                                "description": "",
                                "extract": "Testo della voce C.",
                                "fullurl": "https://it.wikipedia.org/wiki/C",
                            }
                        ]
                    }
                }
            )
        ]
    )
    client = WikipediaClient(cache_dir=tmp_path, session=session)
    article = client.random_article(recent=["A", "B"])
    assert article.title == "C"


def test_random_article_raises_without_cache_or_network(tmp_path, monkeypatch):
    monkeypatch.setattr(wikipedia.time, "sleep", lambda _: None)
    session = FakeSession([requests.ConnectionError("offline")] * 3)
    client = WikipediaClient(cache_dir=tmp_path, session=session)
    with pytest.raises(WikipediaError):
        client.random_article()


def test_last_article_round_trip(tmp_path):
    client = WikipediaClient(cache_dir=tmp_path, session=FakeSession([]))
    article = Article(
        title="Italia",
        description="stato",
        extract="L'Italia è un paese.",
        url="https://it.wikipedia.org/wiki/Italia",
        image_url=None,
        quality="vetrina",
    )
    client.save_last(article)
    assert client.load_last() == article


def test_user_agent_reports_the_package_version():
    from wikiwall import __version__

    assert f"WikiWall/{__version__}" in wikipedia.USER_AGENT


def test_random_article_retries_recent_titles_when_everything_fails(tmp_path, monkeypatch):
    import random

    client = WikipediaClient(cache_dir=tmp_path, session=FakeSession([]))
    monkeypatch.setattr(
        client,
        "quality_titles",
        lambda refresh=False: [("A", "vetrina"), ("B", "qualità")],
    )
    pools = []

    def fake_first(pool, labels, rng):
        pools.append(list(pool))
        if len(pools) == 2:
            return Article(
                title="B",
                description="",
                extract="Testo di B.",
                url="https://it.wikipedia.org/wiki/B",
                image_url=None,
            )
        return None

    monkeypatch.setattr(client, "_first_usable", fake_first)

    article = client.random_article(recent=["A"], rng=random.Random(0))

    assert article.title == "B"
    assert len(pools) == 2
    assert set(pools[1]) == {"A", "B"}


def test_first_usable_skips_broken_titles(tmp_path, monkeypatch):
    class InOrderRng:
        def sample(self, pool, count):
            return list(pool)[:count]

    client = WikipediaClient(cache_dir=tmp_path, session=FakeSession([]))
    article = Article(
        title="B",
        description="",
        extract="Testo di B.",
        url="https://it.wikipedia.org/wiki/B",
        image_url=None,
    )
    calls = []

    def fake_summary(title, quality=""):
        calls.append(title)
        if title == "A":
            raise WikipediaError("non disponibile")
        return article

    monkeypatch.setattr(client, "summary", fake_summary)

    assert client._first_usable(["A", "B"], {"A": "vetrina", "B": "vetrina"}, InOrderRng())
    assert calls == ["A", "B"]
