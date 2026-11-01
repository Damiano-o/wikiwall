import re
from datetime import date

import pytest

from wikiwall.template import build_html, split_lead, truncate_extract
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


def test_truncate_extract_removes_section_headings():
    text = "Introduzione.\n\n== Storia ==\n\nAltro testo."
    assert truncate_extract(text, 100) == "Introduzione. Altro testo."


def test_split_lead_returns_first_sentence_and_rest():
    lead, body = split_lead("Prima frase. Seconda frase.")
    assert lead == "Prima frase."
    assert body == "Seconda frase."


def test_split_lead_handles_single_sentence():
    assert split_lead("Solo una frase") == ("Solo una frase", "")


def test_split_lead_handles_empty_text():
    assert split_lead("") == ("", "")


def test_split_lead_keeps_long_unpunctuated_text_as_body():
    text = "parola " * 40
    lead, body = split_lead(text, max_lead=40)
    assert lead == ""
    assert body == text.strip()


def test_split_lead_uses_long_first_sentence_as_lead():
    text = "Prima frase molto lunga " + "parola " * 20 + ". Seconda frase."
    lead, body = split_lead(text, max_lead=40)
    assert lead.startswith("Prima frase")
    assert lead.endswith(".")
    assert body == "Seconda frase."


def test_split_lead_ignores_abbreviation_inside_parentheses():
    text = (
        'La grande onda (Kanagawa okinami ura, lett. "Una grande onda") '
        "è una xilografia del 1830. È famosa nel mondo."
    )
    lead, body = split_lead(text)
    assert lead.endswith("1830.")
    assert body == "È famosa nel mondo."


def test_split_lead_ignores_period_inside_parentheses():
    text = "Un esempio (vedi fig. 2) è questo. Poi altro."
    lead, body = split_lead(text)
    assert lead == "Un esempio (vedi fig. 2) è questo."
    assert body == "Poi altro."


def test_lead_starting_with_apostrophe_skips_dropcap():
    article = make_article(extract="L'Italia è una repubblica. Il resto della voce.")
    markup = build_html(article, 1920, 1200, today=date(2026, 10, 30))
    assert 'class="lead no-dropcap"' in markup


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


def test_build_html_uses_brand_fonts():
    markup = build_html(make_article(), 1920, 1200)
    assert "Source Serif 4" in markup
    assert "Montserrat" in markup
    assert "data:font/woff2;base64," in markup


def test_build_html_has_click_targets():
    markup = build_html(make_article(), 1920, 1200)
    assert 'id="qr-target"' in markup
    assert 'id="article-link"' in markup
    assert 'id="skip-target"' in markup


def test_build_html_has_skip_action_and_qr_label():
    markup = build_html(make_article(), 1920, 1200)
    assert "Salta voce" in markup
    assert "Clicca il QR" in markup
    assert "o il link" in markup


def test_build_html_uses_lead_and_body():
    article = make_article(
        extract="Prima frase della voce. Seconda frase con altri dettagli.",
    )
    markup = build_html(article, 1920, 1200)
    assert '<p class="lead">Prima frase della voce.</p>' in markup
    assert '<p class="extract">Seconda frase con altri dettagli.</p>' in markup


def test_build_html_keeps_a_250_char_lead_on_small_screens():
    lead = "La voce " + "descrive " * 25 + "con precisione."
    article = make_article(extract=lead + " Seconda frase.")
    markup = build_html(article, 800, 600)
    match = re.search(r'<p class="lead[^"]*">(.*?)</p>', markup)
    assert match is not None
    assert match.group(1).endswith("con precisione.")
    assert "…" not in match.group(1)


def test_build_html_caps_a_very_long_lead_on_small_screens():
    long_lead = "Prima frase " + "molto lunga " * 80 + "fine."
    article = make_article(extract=long_lead + " Seconda frase.")
    markup = build_html(article, 800, 600)
    match = re.search(r'<p class="lead[^"]*">(.*?)</p>', markup)
    assert match is not None
    assert len(match.group(1)) <= 360
    assert '<p class="extract">' in markup


def test_build_html_underlines_article_link():
    markup = build_html(make_article(), 1920, 1200)
    assert "text-decoration: underline" in markup
    assert "↗" in markup


def test_quality_kicker_for_quality_article():
    markup = build_html(make_article(quality="qualità"), 1920, 1200)
    assert "VOCE DI QUALITÀ" in markup


def test_long_title_uses_smaller_font():
    long_title = "Un titolo davvero molto lungo che deve occupare più righe"
    markup = build_html(make_article(title=long_title), 1920, 1200)
    assert "--title-size: clamp(44px, calc(62px * var(--s)), 62px)" in markup


def test_viewport_scales_typography():
    markup = build_html(make_article(), 960, 600)
    assert "--s: 0.5000" in markup
    assert "--title-size: clamp(44px, calc(88px * var(--s)), 88px)" in markup
    assert "--body-size: clamp(15px, calc(21px * var(--s)), 21px)" in markup
    assert "--qr-size: clamp(64px, calc(104px * var(--s)), 104px)" in markup


def test_wide_viewport_uses_height_scale():
    markup = build_html(make_article(), 1920, 1080)
    assert "--s: 0.9000" in markup


def test_invalid_dimensions_are_rejected():
    with pytest.raises(ValueError):
        build_html(make_article(), 0, 600)


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
    assert "--paper: #0e0f11" in markup
    assert "--ink: #f4efe6" in markup
    assert "--accent: #e2b45f" in markup


def test_dark_theme_keeps_a_light_qr_card():
    """Sul fondo scuro il QR resta scuro su carta chiara: lo leggono tutti i lettori."""
    dark = build_html(make_article(), 1920, 1200, theme="dark")
    paper = build_html(make_article(), 1920, 1200, theme="paper")
    assert "--qr-bg: #f4efe6" in dark
    assert "--qr-bg: #fbf7ef" in paper
    assert "data:image/png;base64," in dark
    assert dark.count("data:image/png;base64,") == paper.count("data:image/png;base64,")


def test_the_hero_keeps_a_fallback_letter_under_the_image():
    markup = build_html(make_article(), 1920, 1200)
    assert "hero-letter" in markup
    assert 'class="hero-img"' in markup


def test_both_themes_are_available():
    from wikiwall.config import THEMES as CONFIG_THEMES
    from wikiwall.template import THEMES

    assert tuple(THEMES) == CONFIG_THEMES
