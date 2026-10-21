from __future__ import annotations

import io

from PIL import Image
from playwright.sync_api import Locator, Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    expose_manager,
)

# Size (in CSS px) of an element and the canvas nglview drew inside it
SIZES_JS = """(id) => {
  const out = document.getElementById(id);
  const canvas = out.querySelector('canvas');
  const o = out.getBoundingClientRect();
  const c = canvas.getBoundingClientRect();
  return { out: [o.width, o.height], canvas: [c.width, c.height] };
}"""

MIN_DRAWN_PIXELS = 100

LIVE_VIEWS_JS = "() => window.widgetManager._liveViews.size"

# True once nglview's canvas matches the size of its output element
CANVAS_FILLS_OUTPUT_JS = """(id) => {
  const out = document.getElementById(id);
  const c = out.querySelector('canvas').getBoundingClientRect();
  const o = out.getBoundingClientRect();
  return Math.abs(c.width - o.width) <= 1 && Math.abs(c.height - o.height) <= 1;
}"""


def count_drawn_pixels(locator: Locator) -> int:
    # WebGL canvases can't be read back through a 2D context, so inspect a screenshot
    image = Image.open(io.BytesIO(locator.screenshot())).convert("RGB")
    return sum(1 for r, g, b in image.getdata() if min(r, g, b) < 200)


def wait_until_drawn(page: Page, locator: Locator) -> None:
    for _ in range(50):
        if count_drawn_pixels(locator) > MIN_DRAWN_PIXELS:
            return
        page.wait_for_timeout(200)
    raise AssertionError("nglview never drew anything")


def sizes(page: Page, output_id: str) -> dict[str, list[float]]:
    return page.evaluate(SIZES_JS, output_id)


def test_nglview_renders_visibly(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    canvas = page.locator("#view canvas")
    expect(canvas).to_have_count(1, timeout=30000)
    box = canvas.bounding_box()
    assert box is not None and box["width"] > 0 and box["height"] > 0

    wait_until_drawn(page, canvas)

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_fills_fixed_height_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#view canvas")).to_have_count(1, timeout=30000)

    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="view", timeout=30000)
    wide = sizes(page, "view")
    container = page.locator("#fill_container").bounding_box()
    assert container is not None
    # The output fills the 400px-tall container (minus its 1px borders)
    assert abs(wide["out"][1] - (container["height"] - 2)) <= 1
    assert abs(wide["canvas"][1] - wide["out"][1]) <= 1

    # ... and keeps tracking the container's width when the window resizes
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(
        """(w) => document.getElementById('view').querySelector('canvas')
            .getBoundingClientRect().width < w""",
        arg=wide["canvas"][0] - 100,
        timeout=30000,
    )
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="view", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_respects_explicit_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#fixed canvas")).to_have_count(1, timeout=30000)

    page.wait_for_function(
        """() => document.getElementById('fixed').querySelector('canvas')
            .getBoundingClientRect().height === 250""",
        timeout=30000,
    )
    s = sizes(page, "fixed")
    assert s["out"][1] == 250
    assert s["canvas"][1] == 250
    assert abs(s["canvas"][0] - s["out"][0]) <= 1

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_click_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#picked_atom")).to_have_text("none", timeout=30000)
    canvas = page.locator("#view canvas")
    expect(canvas).to_have_count(1)

    # The single atom is centered in the view; wait for it to be drawn first
    wait_until_drawn(page, canvas)
    canvas.click()
    expect(page.locator("#picked_atom")).to_contain_text("HOH", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_rerender_releases_old_views(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#view canvas")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")
    initial = page.evaluate(LIVE_VIEWS_JS)

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator("#view canvas")).to_have_count(1, timeout=30000)

    expect(page.locator("#view > .lm-Widget")).to_have_count(1)
    assert page.evaluate(LIVE_VIEWS_JS) == initial
    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
