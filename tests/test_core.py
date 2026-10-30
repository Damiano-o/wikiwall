from pathlib import Path

import pytest

from wikiwall import core
from wikiwall.config import Config
from wikiwall.core import WikiWall
from wikiwall.render import RenderResult
from wikiwall.wikipedia import Article, WikipediaError

ARTICLE = Article(
    title="Italia",
    description="stato dell'Europa meridionale",
    extract="L'Italia è un paese dell'Europa meridionale.",
    url="https://it.wikipedia.org/wiki/Italia",
    image_url=None,
    quality="vetrina",
)
FALLBACK = Article(
    title="Dante Alighieri",
    description="poeta italiano",
    extract="Dante Alighieri è stato un poeta italiano.",
    url="https://it.wikipedia.org/wiki/Dante_Alighieri",
    image_url=None,
    quality="qualità",
)


class FakeClient:
    def __init__(self, article=None, error=None, fallback=None):
        self.article = article
        self.error = error
        self.fallback = fallback
        self.saved = []

    def random_article(self, recent=()):
        if self.error is not None:
            raise self.error
        return self.article

    def save_last(self, article):
        self.saved.append(article)

    def load_last(self):
        return self.fallback


class FakeHistory:
    def __init__(self, recent=()):
        self._recent = list(recent)
        self.added = []

    def recent(self):
        return self._recent

    def add(self, title):
        self.added.append(title)


def test_change_renders_and_applies(monkeypatch, tmp_path):
    monkeypatch.setenv("WIKIWALL_HOME", str(tmp_path))
    client = FakeClient(ARTICLE)
    history = FakeHistory()
    applied = []
    rendered = {}

    def fake_render(article, output, width, height, theme):
        rendered.update(
            article=article,
            output=Path(output),
            width=width,
            height=height,
            theme=theme,
        )
        Path(output).write_bytes(b"png")
        return RenderResult(
            path=Path(output),
            qr_box=(10.0, 20.0, 86.0, 86.0),
            link_box=(30.0, 40.0, 200.0, 20.0),
            skip_box=(300.0, 40.0, 120.0, 30.0),
        )

    monkeypatch.setattr(core, "render_article", fake_render)
    monkeypatch.setattr(core, "set_wallpaper", lambda path: applied.append(path))

    app = WikiWall(Config(width=800, height=600), client=client, history=history)
    result = app.change()

    assert result.article == ARTICLE
    assert result.image_path == Path(core.wallpaper_path())
    assert result.theme == "paper"
    assert result.qr_box == (10.0, 20.0, 86.0, 86.0)
    assert result.link_box == (30.0, 40.0, 200.0, 20.0)
    assert result.skip_box == (300.0, 40.0, 120.0, 30.0)
    assert rendered == {
        "article": ARTICLE,
        "output": Path(core.wallpaper_path()),
        "width": 800,
        "height": 600,
        "theme": "paper",
    }
    assert applied == [result.image_path]
    assert history.added == ["Italia"]
    assert client.saved == [ARTICLE]


def test_change_without_apply_does_not_touch_history_or_wallpaper(monkeypatch, tmp_path):
    client = FakeClient(ARTICLE)
    history = FakeHistory()
    applied = []
    output = tmp_path / "preview.png"

    monkeypatch.setattr(
        core,
        "render_article",
        lambda article, out, width, height, theme: RenderResult(Path(out), None, None, None),
    )
    monkeypatch.setattr(core, "set_wallpaper", lambda path: applied.append(path))

    app = WikiWall(Config(width=800, height=600), client=client, history=history)
    app.change(output=output, apply=False, theme="dark")

    assert applied == []
    assert history.added == []
    assert client.saved == [ARTICLE]


def test_change_falls_back_to_last_article(monkeypatch):
    client = FakeClient(error=WikipediaError("offline"), fallback=FALLBACK)
    monkeypatch.setattr(
        core,
        "render_article",
        lambda article, out, width, height, theme: RenderResult(Path(out), None, None, None),
    )

    app = WikiWall(Config(width=800, height=600), client=client, history=FakeHistory())
    result = app.change(apply=False)

    assert result.article == FALLBACK


def test_change_raises_without_offline_fallback(monkeypatch):
    client = FakeClient(error=WikipediaError("offline"))
    app = WikiWall(Config(width=800, height=600), client=client, history=FakeHistory())
    with pytest.raises(WikipediaError):
        app.change(apply=False)
