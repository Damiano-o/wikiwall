from __future__ import annotations

import base64
import html
from datetime import date
from functools import lru_cache
from importlib import resources
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
        "muted": "#5f574d",
        "accent": "#970302",
        "rule": "rgba(25, 23, 20, 0.16)",
        "texture": "rgba(25, 23, 20, 0.05)",
        "qr_bg": "#fbf7ef",
        "qr_ink": "#191714",
    },
    "dark": {
        "paper": "#0e0f11",
        "ink": "#f4efe6",
        "body": "#d9d3c8",
        "muted": "#a49c92",
        "accent": "#e2b45f",
        "rule": "rgba(244, 239, 230, 0.18)",
        "texture": "rgba(255, 255, 255, 0.045)",
        # Il QR resta scuro su carta chiara: così lo leggono tutti gli scanner.
        "qr_bg": "#f4efe6",
        "qr_ink": "#14161a",
    },
}

CSS = """
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden;
}
body {
  --body-size: clamp(15px, calc(21px * var(--s)), 21px);
  --lead-size: clamp(17px, calc(26px * var(--s)), 26px);
  --desc-size: clamp(13px, calc(16px * var(--s)), 16px);
  --small-size: clamp(9px, calc(11px * var(--s)), 11px);
  --qr-size: clamp(64px, calc(104px * var(--s)), 104px);
  --pad-top: clamp(22px, calc(62px * var(--s)), 62px);
  --pad-right: clamp(24px, calc(70px * var(--s)), 70px);
  --pad-bottom: clamp(18px, calc(50px * var(--s)), 50px);
  --pad-left: clamp(28px, calc(76px * var(--s)), 76px);
  --gap: clamp(12px, calc(24px * var(--s)), 24px);
  background: var(--paper);
  color: var(--ink);
  font-family: "Source Serif 4", Georgia, "Times New Roman", serif;
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
  padding: var(--pad-top) var(--pad-right) var(--pad-bottom) var(--pad-left);
  background: var(--paper);
}
.panel::before {
  content: ""; position: absolute; inset: 0;
  background-image: radial-gradient(var(--texture) 0.7px, transparent 0.8px);
  background-size: 5px 5px; opacity: 0.55; pointer-events: none;
}
.panel::after {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0;
  width: clamp(6px, calc(10px * var(--s)), 10px);
  background: var(--accent);
}
.watermark {
  position: absolute; right: calc(-46px * var(--s)); bottom: calc(-150px * var(--s));
  font-family: "Source Serif 4", Georgia, serif;
  font-size: clamp(280px, calc(520px * var(--s)), 520px);
  line-height: 1; color: var(--ink); opacity: 0.035;
  pointer-events: none; user-select: none;
}
.masthead {
  position: relative; z-index: 1;
  display: flex; align-items: flex-start; justify-content: space-between; gap: var(--gap);
}
.brand { display: flex; align-items: center; gap: clamp(8px, calc(14px * var(--s)), 14px); }
.mark {
  width: clamp(32px, calc(44px * var(--s)), 44px);
  height: clamp(32px, calc(44px * var(--s)), 44px);
  display: grid; place-items: center;
  background: var(--ink); color: var(--paper);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: clamp(20px, calc(28px * var(--s)), 28px);
  font-weight: 700; line-height: 1;
}
.brand-name {
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: clamp(12px, calc(15px * var(--s)), 15px);
  font-weight: 700; letter-spacing: 0.24em;
}
.meta {
  display: flex; flex-direction: column; align-items: flex-end;
  text-align: right;
}
.kicker {
  display: block; color: var(--accent);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: clamp(10px, calc(13px * var(--s)), 13px);
  font-weight: 700; letter-spacing: 0.18em;
}
.date {
  display: block; margin-top: clamp(4px, calc(7px * var(--s)), 7px);
  color: var(--muted);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: clamp(9px, calc(12px * var(--s)), 12px);
  letter-spacing: 0.14em;
}
.skip {
  display: inline-flex; align-items: center; gap: 0.35em;
  margin-top: clamp(7px, calc(12px * var(--s)), 12px);
  padding: clamp(4px, calc(6px * var(--s)), 6px) clamp(7px, calc(11px * var(--s)), 11px);
  border: 1px solid var(--rule); border-radius: 999px;
  color: var(--ink); background: transparent;
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: clamp(8px, calc(10px * var(--s)), 10px);
  font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;
  white-space: nowrap;
}
.skip .arrow { color: var(--accent); font-size: 1.15em; }
.rule {
  position: relative; z-index: 1; height: 1px; background: var(--rule);
  margin: clamp(12px, calc(26px * var(--s)), 26px) 0 0;
}
.content {
  position: relative; z-index: 1; flex: 1; min-height: 0;
  padding-top: clamp(14px, calc(34px * var(--s)), 34px);
  display: flex; flex-direction: column; justify-content: center;
}
.title {
  font-family: "Source Serif 4", Georgia, "Times New Roman", serif;
  font-weight: 700; line-height: 0.98; letter-spacing: -0.035em;
  margin: 0; max-width: 980px; text-wrap: balance;
  font-size: var(--title-size);
}
.description {
  margin: clamp(10px, calc(24px * var(--s)), 24px) 0 0;
  max-width: 880px; color: var(--muted);
  font-family: "Source Serif 4", Georgia, serif;
  font-size: var(--desc-size); line-height: 1.4;
}
.lead {
  margin: clamp(12px, calc(28px * var(--s)), 28px) 0 0;
  max-width: 930px; color: var(--body);
  font-family: "Source Serif 4", Georgia, serif;
  font-size: var(--lead-size); line-height: 1.42;
}
.lead::first-letter {
  float: left; font-size: 3.1em; line-height: 0.78;
  padding: 0.06em 0.09em 0 0;
  color: var(--accent); font-weight: 700;
}
.lead.no-dropcap::first-letter {
  float: none; font-size: inherit; line-height: inherit;
  padding: 0; color: inherit; font-weight: inherit;
}
.extract {
  margin: clamp(9px, calc(16px * var(--s)), 16px) 0 0;
  max-width: 930px; color: var(--body);
  font-family: "Source Serif 4", Georgia, serif;
  font-size: var(--body-size); line-height: 1.62;
}
.footer {
  position: relative; z-index: 1;
  display: flex; align-items: flex-end; justify-content: space-between; gap: var(--gap);
  padding-top: clamp(10px, calc(24px * var(--s)), 24px);
  border-top: 1px solid var(--rule);
}
.source { min-width: 0; flex: 1; }
.url {
  display: flex; align-items: baseline; gap: 4px; max-width: 100%;
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: clamp(12px, calc(15px * var(--s)), 15px);
  font-weight: 600; letter-spacing: 0.01em;
  color: var(--ink);
  text-decoration: underline;
  text-decoration-color: var(--accent);
  text-decoration-thickness: 1px;
  text-underline-offset: 5px;
}
.url-text { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.url .arrow { flex-shrink: 0; color: var(--accent); }
.license {
  margin-top: clamp(4px, calc(8px * var(--s)), 8px);
  color: var(--muted);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: var(--small-size);
  letter-spacing: 0.12em; text-transform: uppercase;
  text-wrap: balance;
}
.qr {
  display: flex; align-items: center;
  gap: clamp(8px, calc(14px * var(--s)), 14px);
  flex-shrink: 0;
}
.qr img {
  width: var(--qr-size); height: var(--qr-size); display: block;
  padding: clamp(5px, calc(7px * var(--s)), 7px);
  background: var(--qr-bg); border: 1px solid var(--rule);
}
.qr span {
  width: clamp(70px, calc(100px * var(--s)), 100px);
  color: var(--muted);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: clamp(9px, calc(10px * var(--s)), 10px);
  line-height: 1.45; letter-spacing: 0.12em; text-transform: uppercase;
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
    linear-gradient(180deg, rgba(0, 0, 0, 0.42) 0%, rgba(0, 0, 0, 0) 18%),
    linear-gradient(0deg, rgba(0, 0, 0, 0.48) 0%, rgba(0, 0, 0, 0) 42%),
    linear-gradient(90deg, var(--paper) 0%, rgba(0, 0, 0, 0) 9%);
}
.hero-badge {
  position: absolute; z-index: 2;
  top: clamp(16px, calc(34px * var(--s)), 34px);
  right: clamp(18px, calc(38px * var(--s)), 38px);
  color: rgba(255, 255, 255, 0.86);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: clamp(9px, calc(11px * var(--s)), 11px);
  font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.35);
}
.hero-letter {
  position: absolute; inset: 0; display: grid; place-items: center;
  font-family: "Source Serif 4", Georgia, serif;
  font-size: clamp(220px, calc(420px * var(--s)), 420px);
  line-height: 1; color: rgba(255, 255, 255, 0.13);
}
.hero-caption {
  position: absolute; z-index: 2; left: 0; right: 0;
  bottom: clamp(16px, calc(34px * var(--s)), 34px);
  padding: 0 clamp(18px, calc(38px * var(--s)), 38px);
  color: rgba(255, 255, 255, 0.78);
  font-family: "Montserrat", "Segoe UI", sans-serif;
  font-size: clamp(8px, calc(10px * var(--s)), 10px);
  letter-spacing: 0.18em; text-transform: uppercase;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.45);
}
"""


@lru_cache(maxsize=1)
def _font_face_css() -> str:
    """Embed the open-source Wikimedia brand fonts in the page."""
    try:
        root = resources.files("wikiwall").joinpath("assets").joinpath("fonts")
        montserrat = base64.b64encode(
            root.joinpath("montserrat-variable.woff2").read_bytes()
        ).decode("ascii")
        source_serif = base64.b64encode(
            root.joinpath("source-serif-4-variable.woff2").read_bytes()
        ).decode("ascii")
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        return ""

    return f"""
@font-face {{
  font-family: "Montserrat";
  src: url(data:font/woff2;base64,{montserrat}) format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: block;
}}
@font-face {{
  font-family: "Source Serif 4";
  src: url(data:font/woff2;base64,{source_serif}) format("woff2");
  font-weight: 200 900;
  font-style: normal;
  font-display: block;
}}
"""


def _clean_extract(text: str) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
        if not (line.strip().startswith("==") and line.strip().endswith("=="))
    ]
    return " ".join(" ".join(lines).split())


def truncate_extract(text: str, limit: int = 800) -> str:
    """Trim an extract at a sentence or word boundary, preserving whole words."""
    clean = _clean_extract(text)
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


_ABBREVIATIONS = frozenset(
    {
        "a.c",
        "a.m",
        "art",
        "avv",
        "ca",
        "cap",
        "cfr",
        "cin",
        "cit",
        "col",
        "d.c",
        "dep",
        "dott",
        "ebr",
        "ecc",
        "ed",
        "es",
        "etc",
        "fig",
        "fr",
        "gen",
        "giapp",
        "gr",
        "ibid",
        "ing",
        "ital",
        "lat",
        "lett",
        "max",
        "min",
        "n",
        "n.b",
        "on",
        "op",
        "p.m",
        "p.s",
        "pag",
        "port",
        "pres",
        "prof",
        "rus",
        "sans",
        "sec",
        "sen",
        "sig",
        "sp",
        "ted",
        "ten",
        "trad",
        "v",
        "vol",
        "vs",
    }
)


def _sentence_boundary(text: str) -> int | None:
    """Return the index just after the first real sentence terminator."""
    depth = 0
    quote = ""
    i = 0
    while i < len(text):
        char = text[i]
        if quote:
            if char == quote:
                quote = ""
            elif char in ".!?" and i + 1 < len(text) and text[i + 1] == quote:
                return i + 2
            i += 1
            continue
        if char == '"':
            quote = '"'
            i += 1
            continue
        if char == "“":
            quote = "”"
            i += 1
            continue
        if char == "«":
            quote = "»"
            i += 1
            continue
        if char in "([{":
            depth += 1
            i += 1
            continue
        if char in ")]}":
            depth = max(0, depth - 1)
            i += 1
            continue
        if char in ".!?" and depth == 0:
            if char == "." and text.startswith("...", i):
                i += 3
                continue
            if char == ".":
                j = i - 1
                while j >= 0 and (text[j].isalpha() or text[j] == "."):
                    j -= 1
                word = text[j + 1 : i].lower().strip(".")
                if word in _ABBREVIATIONS:
                    i += 1
                    continue
                if (
                    i > 0
                    and text[i - 1].isdigit()
                    and i + 1 < len(text)
                    and text[i + 1].isdigit()
                ):
                    i += 1
                    continue
            end = i + 1
            if end < len(text) and text[end] in '"”»':
                end += 1
            if end >= len(text) or text[end].isspace():
                return end
        i += 1
    return None


def split_lead(text: str, max_lead: int = 240) -> tuple[str, str]:
    """Split the opening sentence from the rest of an extract."""
    clean = _clean_extract(text)
    if not clean:
        return "", ""

    boundary = _sentence_boundary(clean)
    if boundary is not None:
        return clean[:boundary].strip(), clean[boundary:].strip()

    if len(clean) <= max_lead:
        return clean, ""
    return "", clean


def _title_size(title: str) -> int:
    length = len(title)
    if length <= 22:
        return 100
    if length <= 34:
        return 88
    if length <= 50:
        return 74
    return 62


def _extract_limit(title: str, scale: float = 1.0) -> int:
    length = len(title)
    if length <= 34:
        base = 560
    elif length <= 50:
        base = 500
    else:
        base = 430
    return max(280, int(base * min(scale, 1.0)))


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
        fill_color=palette.get("qr_ink", palette["ink"]),
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
    if width <= 0 or height <= 0:
        raise ValueError("La larghezza e l'altezza devono essere positive.")

    theme = "dark" if theme == "dark" else "paper"
    palette = THEMES[theme]
    today = today or date.today()
    scale = min(width / 1920, height / 1200)

    title_size = _title_size(article.title)
    title_style = (
        f"--title-size: clamp(44px, calc({title_size}px * var(--s)), {title_size}px)"
    )
    lead, rest = split_lead(
        article.extract,
        max_lead=max(150, int(220 * min(scale, 1.0))),
    )
    lead_limit = max(300, int(360 * min(scale, 1.0)))
    if len(lead) > lead_limit:
        cut = lead.rfind(" ", 0, lead_limit)
        if cut < lead_limit // 2:
            cut = lead_limit
        overflow = lead[cut:].strip(" ,;:")
        lead = lead[:cut].rstrip(" ,;:") + "…"
        rest = (overflow + " " + rest).strip()
    body_text = truncate_extract(rest, _extract_limit(article.title, scale))
    kicker = "VOCE IN VETRINA" if article.quality == "vetrina" else "VOCE DI QUALITÀ"
    hero_a, hero_b = _hero_colors(article.title)

    body_style = "; ".join(
        [
            f"--s: {scale:.4f}",
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
        hero_caption = '<div class="hero-caption">Immagine dalla voce · Wikipedia</div>'
    else:
        hero_media = ""
        hero_class = "hero no-image"
        hero_caption = ""
    # L'iniziale resta sotto la foto: se l'immagine non carica viene nascosta
    # dal gestore onerror e la copertina non resta vuota.
    hero_letter = f'<div class="hero-letter">{html.escape(article.title[:1].upper())}</div>'

    description_html = (
        f'<p class="description">{html.escape(article.description)}</p>'
        if article.description
        else ""
    )
    lead_class = "lead"
    if lead and ("'" in lead.split(maxsplit=1)[0] or "’" in lead.split(maxsplit=1)[0]):
        lead_class += " no-dropcap"
    lead_html = f'<p class="{lead_class}">{html.escape(lead)}</p>' if lead else ""
    extract_html = f'<p class="extract">{html.escape(body_text)}</p>' if body_text else ""
    display_url = unquote(article.url).replace("https://", "").replace("http://", "")

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>{html.escape(article.title)}</title>
<style>{_font_face_css()}{CSS}</style>
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
          <span class="skip" id="skip-target">Salta voce <span class="arrow">→</span></span>
        </div>
      </header>
      <div class="rule"></div>
      <main class="content">
        <h1 class="title" style="{title_style}">{html.escape(article.title)}</h1>
        {description_html}
        {lead_html}
        {extract_html}
      </main>
      <footer class="footer">
        <div class="source">
          <div class="url" id="article-link">
            <span class="url-text">{html.escape(display_url)}</span>
            <span class="arrow">↗</span>
          </div>
          <div class="license">Testo e immagini: Wikipedia · CC BY-SA 4.0</div>
        </div>
        <div class="qr">
          <img id="qr-target" src="{_qr_data_uri(article.url, theme)}" alt="QR code">
          <span>Clicca il QR<br>o il link</span>
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


__all__ = ["THEMES", "build_html", "split_lead", "truncate_extract"]
