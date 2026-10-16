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


def test_holoviews_actually_draws_pixels(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # jupyter_bokeh renders the holoviews curve onto a <canvas> (bokeh uses
    # layered canvases, so there may be more than one). A non-blank canvas
    # proves the bokeh model synced to the browser and actually drew.
    expect(page.locator("#hv canvas").first).to_be_visible(timeout=30000)
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#hv")

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
