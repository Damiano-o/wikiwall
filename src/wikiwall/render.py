from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .template import build_html
from .wikipedia import Article

Box = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class RenderResult:
    path: Path
    qr_box: Box | None = None
    link_box: Box | None = None
    skip_box: Box | None = None


def _chrome_candidates() -> list[Path]:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        return []
    base = Path(root) / "ms-playwright"
    found: list[Path] = []
    for pattern in ("chromium-*/chrome-win64/chrome.exe", "chromium-*/chrome-win/chrome.exe"):
        found.extend(base.glob(pattern))
    return sorted(found)


def _bounding_box(locator: object) -> Box | None:
    box = locator.bounding_box()  # type: ignore[attr-defined]
    if box is None:
        return None
    return (box["x"], box["y"], box["width"], box["height"])


def render_article(
    article: Article,
    output: Path,
    width: int,
    height: int,
    theme: str = "paper",
) -> RenderResult:
    """Render *article* to a PNG wallpaper at exactly *width* x *height*."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    markup = build_html(article, width, height, theme)

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise RuntimeError("Playwright non è installato. Esegui: pip install -e .") from exc

    with sync_playwright() as playwright:
        base_options = {"headless": True, "args": ["--hide-scrollbars"]}
        attempts: list[dict[str, object]] = [base_options]
        attempts.extend(
            {**base_options, "executable_path": str(path)}
            for path in reversed(_chrome_candidates())
        )

        browser = None
        errors: list[str] = []
        for options in attempts:
            try:
                browser = playwright.chromium.launch(**options)
                break
            except PlaywrightError as exc:
                errors.append(str(exc))

        if browser is None:
            detail = errors[-1] if errors else "nessun browser disponibile"
            raise RuntimeError(
                f"Chromium non è disponibile. Esegui: wikiwall setup\nDettaglio: {detail}"
            )

        try:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            page.set_default_timeout(30_000)
            page.emulate_media(media="screen")
            page.set_content(markup, wait_until="domcontentloaded")
            page.evaluate("() => document.fonts.ready")
            page.evaluate(
                """() => Promise.all(Array.from(document.images).map((img) => {
                    if (img.complete) return Promise.resolve();
                    return new Promise((resolve) => {
                        img.addEventListener('load', resolve, { once: true });
                        img.addEventListener('error', resolve, { once: true });
                        setTimeout(resolve, 10000);
                    });
                }))"""
            )
            page.wait_for_timeout(250)
            qr_box = _bounding_box(page.locator("#qr-target"))
            link_box = _bounding_box(page.locator("#article-link"))
            skip_box = _bounding_box(page.locator("#skip-target"))
            page.screenshot(path=str(output), full_page=False, type="png")
        finally:
            browser.close()

    return RenderResult(output, qr_box, link_box, skip_box)


__all__ = ["Box", "RenderResult", "render_article"]
