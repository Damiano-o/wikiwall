from __future__ import annotations

import base64
import html
from datetime import date
from io import BytesIO
from urllib.parse import unquote

import qrcode

from .wikipedia import Article

ITALIAN_MONTHS = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)

THEMES: dict[str, dict[str, str]] = {
    "paper": {
        "paper": "#f3ede2",
        "ink": "#191714",
        "body": "#2b2721",
        "muted": "#6f675c",
        "accent": "#b23a2b",
        "rule": "rgba(25, 23, 20, 0.16)",
        "texture": "rgba(25, 23, 20, 0.05)",
        "qr_bg": "#fbf7ef",
    },
    "dark": {
        "paper": "#121212",
        "ink": "#f2ede4",
        "body": "#ddd7cd",
        "muted": "#a9a196",
        "accent": "#e0b45c",
        "rule": "rgba(242, 237, 228, 0.18)",
        "texture": "rgba(255, 255, 255, 0.04)",
        "qr_bg": "#18191b",
    },
}

CSS = """
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden;
}
body {
  background: var(--paper);
  color: var(--ink);
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
.canvas {
  width: 100vw; height: 100vh;
  display: grid; grid-template-columns: 58% 42%;
  overflow: hidden;
}
.panel {
  position: relative; overflow: hidden;
  display: flex; flex-direction: column;
  padding: 62px 70px 50px 76px;
  background: var(--paper);
}
.panel::before {
  content: ""; position: absolute; inset: 0;
  background-image: radial-gradient(var(--texture) 0.7px, transparent 0.8px);
  background-size: 5px 5px; opacity: 0.55; pointer-events: none;
}
.panel::after {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 10px;
  background: var(--accent);
}
.watermark {
  position: absolute; right: -46px; bottom: -150px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 520px; line-height: 1; color: var(--ink); opacity: 0.035;
  pointer-events: none; user-select: none;
}
.masthead {
  position: relative; z-index: 1;
  display: flex; align-items: flex-start; justify-content: space-between; gap: 24px;
}
.brand { display: flex; align-items: center; gap: 14px; }
.mark {
  width: 44px; height: 44px; display: grid; place-items: center;
  background: var(--ink); color: var(--paper);
  font-family: Georgia, "Times New Roman", serif;
  font-size: 28px; font-weight: 700; line-height: 1;
}
.brand-name { font-size: 15px; font-weight: 700; letter-spacing: 0.24em; }
.meta { text-align: right; }
.kicker {
  display: block; color: var(--accent);
  font-size: 13px; font-weight: 700; letter-spacing: 0.18em;
}
.date {
  display: block; margin-top: 7px; color: var(--muted);
  font-size: 12px; letter-spacing: 0.14em;
}
.rule {
  position: relative; z-index: 1; height: 1px; background: var(--rule);
  margin: 26px 0 0;
}
.content {
  position: relative; z-index: 1; flex: 1; min-height: 0;
  padding-top: 34px; display: flex; flex-direction: column; justify-content: center;
}
.title {
  font-family: Georgia, "Times New Roman", "Palatino Linotype", serif;
  font-weight: 700; line-height: 0.98; letter-spacing: -0.035em;
  margin: 0; max-width: 980px; text-wrap: balance;
}
.description {
  margin: 24px 0 0; max-width: 880px;
  font-family: Georgia, "Times New Roman", serif; font-style: italic;
  font-size: 24px; line-height: 1.35; color: var(--muted);
}
.extract {
  margin: 30px 0 0; max-width: 930px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 23px; line-height: 1.56; color: var(--body);
}
.extract::first-letter {
  float: left; font-size: 4.15em; line-height: 0.78;
  padding: 0.06em 0.09em 0 0;
  color: var(--accent); font-weight: 700;
}
.footer {
  position: relative; z-index: 1;
  display: flex; align-items: flex-end; justify-content: space-between; gap: 28px;
  padding-top: 24px; border-top: 1px solid var(--rule);
}
.source { min-width: 0; flex: 1; }
.url {
  font-size: 15px; font-weight: 600; letter-spacing: 0.01em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: var(--ink);
}
.license {
  margin-top: 8px; color: var(--muted);
  font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
}
.qr { display: flex; align-items: center; gap: 14px; flex-shrink: 0; }
.qr img {
  width: 86px; height: 86px; display: block;
  padding: 7px; background: var(--qr-bg); border: 1px solid var(--rule);
}
.qr span {
  width: 92px; color: var(--muted);
  font-size: 10px; line-height: 1.45; letter-spacing: 0.12em; text-transform: uppercase;
}
.hero {
  position: relative; overflow: hidden;
  background: linear-gradient(135deg, var(--hero-a), var(--hero-b));
}
.hero-img {
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; filter: saturate(0.92) contrast(1.02);
}
.hero::after {
  content: ""; position: absolute; inset: 0;
  background:
    linear-gradient(90deg, var(--paper) 0%, rgba(0, 0, 0, 0) 9%),
    linear-gradient(0deg, rgba(0, 0, 0, 0.38) 0%, rgba(0, 0, 0, 0) 38%);
}
.hero-badge {
  position: absolute; z-index: 2; top: 34px; right: 38px;
  color: rgba(255, 255, 255, 0.86);
  font-size: 11px; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.35);
}
.hero-letter {
  position: absolute; inset: 0; display: grid; place-items: center;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 420px; line-height: 1; color: rgba(255, 255, 255, 0.13);
}
.hero-caption {
  position: absolute; z-index: 2; left: 0; right: 0; bottom: 34px;
  padding: 0 38px; color: rgba(255, 255, 255, 0.72);
  font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
}
"""


def truncate_extract(text: str, limit: int = 800) -> str:
    """Trim an extract at a sentence or word boundary, preserving whole words."""
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean

    window = clean[:limit]
    cut = -1
    for marker in (". ", "! ", "? "):
        position = window.rfind(marker)
        if position > cut:
            cut = position + 1

    if cut >= int(limit * 0.55):
        return clean[:cut].rstrip()

    space = window.rfind(" ")
    if space > 0:
        return clean[:space].rstrip(" ,;:") + "…"
    return window.rstrip() + "…"


def _title_size(title: str) -> int:
    length = len(title)
    if length <= 22:
        return 100
    if length <= 34:
        return 88
    if length <= 50:
        return 74
    return 62


def _extract_limit(title: str) -> int:
    length = len(title)
    if length <= 34:
        return 820
    if length <= 50:
        return 720
    return 620


def _hero_colors(title: str) -> tuple[str, str]:
    hue = sum(ord(char) for char in title) % 360
    return (
        f"hsl({hue} 32% 30%)",
        f"hsl({(hue + 42) % 360} 38% 13%)",
    )


def _qr_data_uri(url: str, theme: str) -> str:
    palette = THEMES[theme]
    code = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=0,
    )
    code.add_data(url)
    code.make(fit=True)
    image = code.make_image(
        fill_color=palette["ink"],
        back_color=palette["qr_bg"],
    ).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _date_text(today: date) -> str:
    return f"{today.day} {ITALIAN_MONTHS[today.month - 1]} {today.year}".upper()


def build_html(
    article: Article,
    width: int,
    height: int,
    theme: str = "paper",
    today: date | None = None,
) -> str:
    theme = "dark" if theme == "dark" else "paper"
    palette = THEMES[theme]
    today = today or date.today()

    title_size = _title_size(article.title)
    extract = truncate_extract(article.extract, _extract_limit(article.title))
    kicker = "VOCE IN VETRINA" if article.quality == "vetrina" else "VOCE DI QUALITÀ"
    hero_a, hero_b = _hero_colors(article.title)

    body_style = "; ".join(
        [
            f"--paper: {palette['paper']}",
            f"--ink: {palette['ink']}",
            f"--body: {palette['body']}",
            f"--muted: {palette['muted']}",
            f"--accent: {palette['accent']}",
            f"--rule: {palette['rule']}",
            f"--texture: {palette['texture']}",
            f"--qr-bg: {palette['qr_bg']}",
            f"--hero-a: {hero_a}",
            f"--hero-b: {hero_b}",
        ]
    )

    if article.image_url:
        hero_media = (
            f'<img class="hero-img" src="{html.escape(article.image_url, quote=True)}" '
            'alt="" onerror="this.remove()">'
        )
        hero_class = "hero"
        hero_letter = ""
        hero_caption = '<div class="hero-caption">Immagine dalla voce · Wikipedia</div>'
    else:
        hero_media = ""
        hero_class = "hero no-image"
        hero_letter = f'<div class="hero-letter">{html.escape(article.title[:1].upper())}</div>'
        hero_caption = ""

    description_html = (
        f'<p class="description">{html.escape(article.description)}</p>'
        if article.description
        else ""
    )
    display_url = unquote(article.url).replace("https://", "").replace("http://", "")

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>{html.escape(article.title)}</title>
<style>{CSS}</style>
</head>
<body style="{body_style}">
  <div class="canvas">
    <section class="panel">
      <div class="watermark">W</div>
      <header class="masthead">
        <div class="brand">
          <span class="mark">W</span>
          <span class="brand-name">WIKIPEDIA</span>
        </div>
        <div class="meta">
          <span class="kicker">{kicker}</span>
          <span class="date">{_date_text(today)}</span>
        </div>
      </header>
      <div class="rule"></div>
      <main class="content">
        <h1 class="title" style="font-size: {title_size}px">{html.escape(article.title)}</h1>
        {description_html}
        <p class="extract">{html.escape(extract)}</p>
      </main>
      <footer class="footer">
        <div class="source">
          <div class="url">{html.escape(display_url)}</div>
          <div class="license">Testo e immagini: Wikipedia · CC BY-SA 4.0</div>
        </div>
        <div class="qr">
          <img src="{_qr_data_uri(article.url, theme)}" alt="QR code">
          <span>Inquadra per aprire la voce</span>
        </div>
      </footer>
    </section>
    <aside class="{hero_class}">
      {hero_media}
      {hero_letter}
      <div class="hero-badge">IT · WIKIPEDIA</div>
      {hero_caption}
    </aside>
  </div>
</body>
</html>"""


__all__ = ["THEMES", "build_html", "truncate_extract"]
