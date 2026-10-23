from __future__ import annotations

import struct
import zlib

from playwright.sync_api import Page, Route, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)

# jupyter_bokeh's frontend first tries to load its extension JS from a path
# that 404s (also on pre-existing bokeh apps) before falling back to the CDN.
BOKEH_404 = "@bokeh/jupyter_bokeh.js"

TILE_URL_GLOB = "**/*.tile.openstreetmap.org/**"
TILE_RGB = (170, 211, 223)

ALL_OUTPUTS = ("#tiles", "#fixed", "#dynamic", "#polygons")

# Defines canvasesUnder(sel): the canvases under a selector, piercing shadow
# roots (bokeh renders into shadow DOM, which querySelectorAll doesn't reach)
CANVASES_UNDER_JS = """
  const canvasesUnder = (sel) => {
    const canvases = [];
    const walk = (root) => {
      if (root.tagName === 'CANVAS') canvases.push(root);
      for (const el of root.querySelectorAll('*')) {
        if (el.tagName === 'CANVAS') canvases.push(el);
        if (el.shadowRoot) walk(el.shadowRoot);
      }
    };
    for (const root of document.querySelectorAll(sel)) walk(root);
    return canvases;
  };
"""

# Bounding box of the largest canvas under a selector
CANVAS_RECT_JS = (
    "(sel) => {"
    + CANVASES_UNDER_JS
    + """
  let best = null;
  for (const c of canvasesUnder(sel)) {
    const r = c.getBoundingClientRect();
    if (!best || r.width * r.height > best.width * best.height) best = r;
  }
  return best && { width: best.width, height: best.height };
}"""
)

# Counts pixels close to (r, g, b) on the canvases under a selector
COUNT_COLOR_PIXELS_JS = (
    "([sel, [r, g, b]]) => {"
    + CANVASES_UNDER_JS
    + """
  let n = 0;
  for (const c of canvasesUnder(sel)) {
    let ctx = null;
    try { ctx = c.getContext('2d'); } catch (e) { continue; }
    if (!ctx || !c.width || !c.height) continue;
    const d = ctx.getImageData(0, 0, c.width, c.height).data;
    for (let i = 0; i < d.length; i += 4) {
      if (d[i + 3] > 200 && Math.abs(d[i] - r) < 12 &&
          Math.abs(d[i + 1] - g) < 12 && Math.abs(d[i + 2] - b) < 12) n++;
    }
  }
  return n;
}"""
)

# x position of the leftmost red pixel on the first drawable canvas of a selector
LEFTMOST_RED_JS = (
    "(sel) => {"
    + CANVASES_UNDER_JS
    + """
  for (const c of canvasesUnder(sel)) {
    let ctx = null;
    try { ctx = c.getContext('2d'); } catch (e) { continue; }
    if (!ctx || !c.width || !c.height) continue;
    const d = ctx.getImageData(0, 0, c.width, c.height).data;
    for (let x = 0; x < c.width; x++)
      for (let y = 0; y < c.height; y++) {
        const i = (y * c.width + x) * 4;
        if (d[i + 3] > 200 && d[i] > 180 && d[i + 1] < 90 && d[i + 2] < 90) return x;
      }
  }
  return -1;
}"""
)

# True once the first canvas under a selector spans most of the output's box
CANVAS_FILLS_OUTPUT_JS = (
    "(sel) => {"
    + CANVASES_UNDER_JS
    + """
  const o = document.querySelector(sel).getBoundingClientRect();
  const cs = canvasesUnder(sel);
  if (!cs.length) return false;
  const c = cs[0].getBoundingClientRect();
  return c.width >= 0.9 * o.width && c.height >= 0.9 * o.height;
}"""
)


def solid_png(rgb: tuple[int, int, int], size: int = 256) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    row = b"\x00" + bytes(rgb) * size
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(row * size))
        + chunk(b"IEND", b"")
    )


def serve_fake_tiles(page: Page) -> list[str]:
    # Keeps the tests hermetic: no dependence on (or load on) the real tile server
    requested: list[str] = []
    tile = solid_png(TILE_RGB)

    def handle(route: Route) -> None:
        requested.append(route.request.url)
        route.fulfill(
            status=200,
            content_type="image/png",
            body=tile,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    page.route(TILE_URL_GLOB, handle)
    return requested


def assert_draws_pixels(page: Page, selector: str) -> None:
    expect(page.locator(f"{selector} canvas").first).to_be_visible(timeout=30000)
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, selector), selector


def test_geoviews_actually_draws_pixels(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    tile_requests = serve_fake_tiles(page)
    page.goto(local_app.url)

    for selector in ALL_OUTPUTS:
        assert_draws_pixels(page, selector)

    # The tile layer really made it to the browser and was painted: the page
    # requested tiles and the (fake) tile color is on the canvas
    page.wait_for_function(
        "([sel, rgb]) => (" + COUNT_COLOR_PIXELS_JS + ")([sel, rgb]) > 1000",
        arg=["#tiles", list(TILE_RGB)],
        timeout=30000,
    )
    assert tile_requests

    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))


def test_geoviews_fills_container_and_respects_explicit_size(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    serve_fake_tiles(page)
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(local_app.url)

    for selector in ("#tiles", "#polygons"):
        assert_draws_pixels(page, selector)

    # In a fixed-height card, a responsive map fills the output's box (the
    # remainder is bokeh's own margin around the plot)
    for selector in ("#tiles", "#polygons"):
        page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg=selector, timeout=30000)
        out = page.locator(selector).bounding_box()
        canvas = page.evaluate(CANVAS_RECT_JS, selector)
        card = page.locator(f"{selector}_card").bounding_box()
        assert out and canvas and card
        assert card["height"] == 400
        assert out["height"] >= 0.8 * card["height"]
        assert canvas["width"] >= 0.9 * out["width"], (selector, canvas, out)
        assert canvas["height"] >= 0.9 * out["height"], (selector, canvas, out)
        assert canvas["width"] <= out["width"] and canvas["height"] <= out["height"]

    # An explicit width/height is not stretched to the card
    assert_draws_pixels(page, "#fixed")
    fixed = page.evaluate(CANVAS_RECT_JS, "#fixed")
    assert fixed["width"] == 350 and fixed["height"] == 250, fixed

    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))


def test_geoviews_fill_tracks_container_resize(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    serve_fake_tiles(page)
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(local_app.url)
    assert_draws_pixels(page, "#tiles")

    page.wait_for_function(
        f"() => ({CANVAS_RECT_JS})('#tiles').width > 250", timeout=30000
    )
    wide = page.evaluate(CANVAS_RECT_JS, "#tiles")["width"]

    page.set_viewport_size({"width": 700, "height": 900})
    page.wait_for_function(
        f"(w) => ({CANVAS_RECT_JS})('#tiles').width < w - 50", arg=wide, timeout=30000
    )

    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))


def test_geoviews_dynamicmap_widget_roundtrip(page: Page, local_app) -> None:
    # Changing the DynamicMap's widget calls back into Python, which returns
    # points at a new longitude
    errors, failed_requests = collect_errors(page)
    serve_fake_tiles(page)
    page.goto(local_app.url)

    assert_draws_pixels(page, "#dynamic")
    spinner = page.locator("#dynamic .bk-input").first
    expect(spinner).to_be_visible(timeout=30000)

    left_before = page.evaluate(LEFTMOST_RED_JS, "#dynamic")
    assert left_before >= 0

    spinner.click()
    spinner.fill("100")
    spinner.press("Enter")
    expect(spinner).to_have_value("100")

    page.wait_for_function(
        f"(left) => ({LEFTMOST_RED_JS})('#dynamic') > left + 50",
        arg=left_before,
        timeout=10000,
    )

    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))


def test_geoviews_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    serve_fake_tiles(page)
    page.goto(local_app.url)

    assert_draws_pixels(page, "#tiles")
    expect(page.locator("#render_count")).to_have_text("0")
    n_canvases = page.locator("#tiles canvas").count()

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    # The old view must be disposed (i.e., no accumulation of canvases) ...
    expect(page.locator("#tiles canvas")).to_have_count(n_canvases)

    # ... and the new widget still draws
    assert_draws_pixels(page, "#tiles")

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests, allowed_404s=(BOKEH_404,))
