from datetime import date

from wikiwall.template import build_html, truncate_extract
from wikiwall.wikipedia import Article


def make_article(**overrides):
    values = {
        "title": "La grande onda di Kanagawa",
        "description": "xilografia di Katsushika Hokusai",
        "extract": (
            "La grande onda di Kanagawa è una xilografia in stile ukiyo-e del pittore "
            "giapponese Katsushika Hokusai realizzata tra il 1830 e il 1833. È la prima "
            "e più celebre opera della serie Trentasei vedute del Monte Fuji."
        ),
        "url": "https://it.wikipedia.org/wiki/La_grande_onda_di_Kanagawa",
        "image_url": "https://example.org/onda.jpg",
        "quality": "vetrina",
    }
    values.update(overrides)
    return Article(**values)


def test_truncate_extract_short_text_is_unchanged():
    assert truncate_extract("Ciao   mondo.", 100) == "Ciao mondo."


def test_truncate_extract_stops_at_sentence():
    text = "Prima frase. Seconda frase. Terza frase."
    assert truncate_extract(text, 20) == "Prima frase."


def test_truncate_extract_falls_back_to_word_boundary():
    text = "parola " * 30
    result = truncate_extract(text, 25)
    assert result.endswith("…")
    assert not result.endswith("parol…")


def test_build_html_escapes_content():
    article = make_article(
        title="<script>alert(1)</script>",
        description="<b>descrizione</b>",
        extract="<b>testo</b> della voce",
    )
    markup = build_html(article, 1920, 1200, today=date(2026, 10, 30))
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in markup
    assert "&lt;b&gt;descrizione&lt;/b&gt;" in markup
    assert "&lt;b&gt;testo&lt;/b&gt;" in markup
    assert "<script>alert(1)</script>" not in markup


def test_build_html_contains_article_fields():
    article = make_article()
    markup = build_html(article, 1920, 1200, today=date(2026, 10, 30))
    assert "La grande onda di Kanagawa" in markup
    assert "xilografia di Katsushika Hokusai" in markup
    assert "it.wikipedia.org/wiki/La_grande_onda_di_Kanagawa" in markup
    assert "data:image/png;base64," in markup
    assert "Testo e immagini: Wikipedia · CC BY-SA 4.0" in markup
    assert "30 OTTOBRE 2026" in markup
    assert "VOCE IN VETRINA" in markup


def test_quality_kicker_for_quality_article():
    markup = build_html(make_article(quality="qualità"), 1920, 1200)
    assert "VOCE DI QUALITÀ" in markup


def test_long_title_uses_smaller_font():
    long_title = "Un titolo davvero molto lungo che deve occupare più righe"
    markup = build_html(make_article(title=long_title), 1920, 1200)
    assert "font-size: 62px" in markup


def test_no_image_uses_gradient_and_initial():
    markup = build_html(make_article(image_url=None), 1920, 1200)
    assert 'class="hero no-image"' in markup
    assert "hero-letter" in markup
    assert '<img class="hero-img"' not in markup


def test_image_article_uses_img_tag():
    markup = build_html(make_article(), 1920, 1200)
    assert 'class="hero"' in markup
    assert 'class="hero-img"' in markup
    assert "https://example.org/onda.jpg" in markup


def test_dark_theme_uses_dark_palette():
    markup = build_html(make_article(), 1920, 1200, theme="dark")
    assert "--paper: #121212" in markup
    assert "--ink: #f2ede4" in markup
