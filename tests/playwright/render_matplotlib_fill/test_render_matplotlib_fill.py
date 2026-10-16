from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# True once the ipympl canvas fills the output container's width and fits
# within its height (i.e., no overflow). ipympl draws the figure at a fixed
# pixel size by default; shinywidgets drives it to the container size.
CANVAS_FILLS_JS = """() => {
  const out = document.querySelector('#mpl');
  const canvas = out && out.querySelector('.jupyter-matplotlib-canvas-div canvas');
  if (!canvas) return false;
  const o = out.getBoundingClientRect();
  const c = canvas.getBoundingClientRect();
  return c.width >= 0.95 * o.width && c.height <= o.height && c.height >= 0.6 * o.height;
}"""

CANVAS_WIDTH_JS = """() => {
  const canvas = document.querySelector('#mpl .jupyter-matplotlib-canvas-div canvas');
  return canvas ? canvas.getBoundingClientRect().width : -1;
}"""


def test_matplotlib_fills_fillable_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(local_app.url)

    expect(page.locator("#mpl canvas").first).to_be_visible(timeout=30000)

    # The figure should grow from its natural size (640x480) to fill the card
    page.wait_for_function(CANVAS_FILLS_JS, timeout=30000)
    wide = page.evaluate(CANVAS_WIDTH_JS)

    # ... and it should track the container when the window resizes
    page.set_viewport_size({"width": 640, "height": 420})
    page.wait_for_function(CANVAS_FILLS_JS, timeout=30000)
    narrow = page.evaluate(CANVAS_WIDTH_JS)

    assert narrow < wide, (
        f"canvas width should shrink with the window ({wide} -> {narrow})"
    )

    assert_no_unexpected_errors(errors, failed_requests)
