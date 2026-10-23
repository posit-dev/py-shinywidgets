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

# x-extent [x0, x1] (in data units) of the datashader image the browser is
# currently displaying, from the bokeh Image glyph's data source. (Bokeh.index
# retains the detached root views of previous renders, so only look at views
# that are still in the page.)
IMAGE_EXTENT_JS = """() => {
  const extents = [];
  const walk = (view) => {
    const m = view.model;
    if (m && m.glyph && m.glyph.type === 'Image') {
      const d = m.data_source.data;
      extents.push([d.x[0], d.x[0] + d.dw[0]]);
    }
    for (const c of (view.child_views ?? [])) walk(c);
    if (view.renderer_views) for (const c of view.renderer_views.values()) walk(c);
  };
  for (const v of Object.values(Bokeh.index)) if (v.el.isConnected) walk(v);
  return extents.length === 1 ? extents[0] : null;
}"""

# x-range [lo, hi] of the image datashader most recently produced on the
# server (the app's #aggregations output lists each one as "lo,hi")
SERVER_RANGE_JS = """() => {
  const pairs = document.querySelector('#aggregations').innerText.trim().split(' ');
  return pairs[pairs.length - 1].split(',').map(Number);
}"""

# True once the browser displays the server's latest aggregation, and that
# image is narrower than `maxWidth` and starts right of `minX0`
SHOWS_SERVER_IMAGE_JS = f"""({{ maxWidth, minX0 }}) => {{
  const img = ({IMAGE_EXTENT_JS})();
  const srv = ({SERVER_RANGE_JS})();
  return img !== null &&
    Math.abs(img[0] - srv[0]) < 0.01 && Math.abs(img[1] - srv[1]) < 0.01 &&
    img[1] - img[0] < maxWidth && img[0] > minX0;
}}"""


def wait_for_server_image(
    page: Page, *, max_width: float = float("inf"), min_x0: float = float("-inf")
) -> None:
    page.wait_for_function(
        SHOWS_SERVER_IMAGE_JS,
        arg={"maxWidth": max_width, "minX0": min_x0},
        timeout=10000,
    )


def plot_center(page: Page) -> tuple[float, float, float]:
    box = page.locator("#points canvas").first.bounding_box()
    assert box is not None
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, box["width"]


def assert_reaggregates_on_zoom(page: Page) -> None:
    expect(page.locator("#points canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#aggregations")).not_to_be_empty(timeout=30000)
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#points")
    wait_for_server_image(page)
    x0, x1 = page.evaluate(IMAGE_EXTENT_JS)

    # Zoom in with the wheel (hvPlot activates bokeh's wheel zoom tool by
    # default). Bokeh reports the new range to the server, where holoviews
    # re-runs datashader for just that range, and the re-aggregated (narrower)
    # image is sent back to the browser -- all without further client input.
    cx, cy, _ = plot_center(page)
    page.mouse.move(cx, cy)
    for _ in range(5):
        page.mouse.wheel(0, -200)
    wait_for_server_image(page, max_width=(x1 - x0) / 2)


def assert_reaggregates_on_pan(page: Page) -> None:
    x0, x1 = page.evaluate(IMAGE_EXTENT_JS)

    # Drag the plot to the left (pan is hvPlot's default drag tool), revealing
    # data to the right, which the server aggregates
    cx, cy, width = plot_center(page)
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx - width / 3, cy, steps=10)
    page.mouse.up()
    wait_for_server_image(page, min_x0=x0 + (x1 - x0) / 5)


def test_datashader_reaggregates_on_zoom(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    assert_reaggregates_on_zoom(page)
    assert_reaggregates_on_pan(page)

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
