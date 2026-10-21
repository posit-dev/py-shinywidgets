from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)

# jupyter_bokeh's frontend first tries to load its extension JS from a path
# that 404s before falling back to the CDN (see render_holoviews tests).
BOKEH_404 = "@bokeh/jupyter_bokeh.js"

# Width (in data units) of the datashader image the browser is currently
# displaying, i.e., the `dw` column of the bokeh Image glyph's data source.
# (Bokeh.index retains the detached root views of previous renders, so only
# look at views that are still in the page.)
IMAGE_WIDTH_JS = """() => {
  const widths = [];
  const walk = (view) => {
    const m = view.model;
    if (m && m.glyph && m.glyph.type === 'Image') widths.push(m.data_source.data.dw[0]);
    for (const c of (view.child_views ?? [])) walk(c);
    if (view.renderer_views) for (const c of view.renderer_views.values()) walk(c);
  };
  for (const v of Object.values(Bokeh.index)) if (v.el.isConnected) walk(v);
  return widths.length === 1 ? widths[0] : null;
}"""


# Width of the x-range of the image datashader most recently produced on the
# server (the app's #aggregations output lists each one as "lo,hi")
SERVER_WIDTH_JS = """() => {
  const pairs = document.querySelector('#aggregations').innerText.trim().split(' ');
  const [lo, hi] = pairs[pairs.length - 1].split(',').map(Number);
  return hi - lo;
}"""


def zoom_in(page: Page) -> None:
    # hvPlot activates bokeh's wheel zoom tool by default
    box = page.locator("#points canvas").first.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    for _ in range(5):
        page.mouse.wheel(0, -200)


def assert_reaggregates_on_zoom(page: Page) -> None:
    expect(page.locator("#points canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#aggregations")).not_to_be_empty(timeout=30000)
    page.wait_for_function(f"({IMAGE_WIDTH_JS})() !== null", timeout=30000)
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#points")

    full_width = page.evaluate(IMAGE_WIDTH_JS)
    assert abs(page.evaluate(SERVER_WIDTH_JS) - full_width) < 0.01

    zoom_in(page)

    # Bokeh reports the new range to the server, where holoviews re-runs
    # datashader for just that range, and the re-aggregated (narrower) image
    # is sent back to the browser -- all without any further client input
    page.wait_for_function(
        f"(full) => ({IMAGE_WIDTH_JS})() < full / 2",
        arg=full_width,
        timeout=10000,
    )
    page.wait_for_function(
        f"(width) => Math.abs(({SERVER_WIDTH_JS})() - width) < 0.01",
        arg=page.evaluate(IMAGE_WIDTH_JS),
        timeout=10000,
    )


def test_datashader_reaggregates_on_zoom(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    assert_reaggregates_on_zoom(page)

    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))


def test_datashader_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#points canvas").first).to_be_visible(timeout=30000)
    n_canvases = page.locator("#points canvas").count()

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    # Old views are disposed (no accumulation of canvases) ...
    expect(page.locator("#points canvas")).to_have_count(n_canvases)
    # ... and the replacement still re-aggregates on zoom
    assert_reaggregates_on_zoom(page)

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))
