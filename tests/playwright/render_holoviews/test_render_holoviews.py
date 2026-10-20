from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)

# jupyter_bokeh's frontend first tries to load its extension JS from a path
# that 404s (also on pre-existing bokeh apps) before falling back to the CDN.
BOKEH_404 = "@bokeh/jupyter_bokeh.js"

# Every output in the app (covers holoviews elements, overlays, layouts,
# .opts(), DynamicMap, and hvPlot from pandas, with and without grouping)
ALL_OUTPUTS = (
    "#hv",
    "#overlay",
    "#layout",
    "#styled",
    "#dynamic",
    "#hvplot_line",
    "#hvplot_group",
)


def assert_draws_pixels(page: Page, selector: str) -> None:
    # Panel/jupyter_bokeh renders onto <canvas> (bokeh uses layered canvases,
    # so there may be more than one). A non-blank canvas proves the bokeh
    # model synced to the browser and actually drew.
    expect(page.locator(f"{selector} canvas").first).to_be_visible(timeout=30000)
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, selector), selector


def test_holoviews_actually_draws_pixels(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    for selector in ALL_OUTPUTS:
        assert_draws_pixels(page, selector)

    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))


def test_holoviews_opts_are_applied(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    assert_draws_pixels(page, "#styled")

    # The .opts(color="red") should surface on the canvas (bokeh draws titles
    # and glyphs into the canvas, not the DOM). Also proves the canvas is
    # readable this way (i.e., not tainted).
    has_red = page.evaluate(
        """(sel) => {
          const canvases = [];
          const walk = (root) => {
            if (root.tagName === 'CANVAS') canvases.push(root);
            for (const el of root.querySelectorAll('*')) {
              if (el.tagName === 'CANVAS') canvases.push(el);
              if (el.shadowRoot) walk(el.shadowRoot);
            }
          };
          for (const root of document.querySelectorAll(sel)) walk(root);
          for (const c of canvases) {
            let ctx = null;
            try { ctx = c.getContext('2d'); } catch (e) { continue; }
            if (!ctx || !c.width || !c.height) continue;
            const d = ctx.getImageData(0, 0, c.width, c.height).data;
            let red = 0;
            for (let i = 0; i < d.length; i += 4 * 7) {
              if (d[i + 3] > 200 && d[i] > 150 && d[i + 1] < 80 && d[i + 2] < 80) red++;
            }
            if (red > 10) return true;
          }
          return false;
        }""",
        "#styled",
    )
    assert has_red

    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))


def test_holoviews_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#hv canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    n_canvases = page.locator("#hv canvas").count()

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    # Re-rendering replaces the widget, but the old view must be disposed
    # (i.e., no accumulation of canvases) ...
    expect(page.locator("#hv canvas")).to_have_count(n_canvases)

    # ... and the new widget still draws
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#hv")

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))
