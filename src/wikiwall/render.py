from __future__ import annotations

import os
from pathlib import Path

from .template import build_html
from .wikipedia import Article


def _chrome_candidates() -> list[Path]:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        return []
    base = Path(root) / "ms-playwright"
    found: list[Path] = []
    for pattern in ("chromium-*/chrome-win64/chrome.exe", "chromium-*/chrome-win/chrome.exe"):
        found.extend(base.glob(pattern))
    return sorted(found)


def render_article(
    article: Article,
    output: Path,
    width: int,
    height: int,
    theme: str = "paper",
) -> Path:
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
                "Chromium non è disponibile. Esegui: wikiwall setup\n"
                f"Dettaglio: {detail}"
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
            page.screenshot(path=str(output), full_page=False, type="png")
        finally:
            browser.close()

    return output


__all__ = ["render_article"]
