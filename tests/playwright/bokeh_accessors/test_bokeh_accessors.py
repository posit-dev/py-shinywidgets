from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Page coordinates of a data point, via the plot view's scales.
POINT_JS = """([x, y]) => {
  const view = [...window.Bokeh.index.values ? window.Bokeh.index.values() : Object.values(window.Bokeh.index)][0];
  const canvas = view.canvas_view.el.getBoundingClientRect();
  return [canvas.left + view.frame.x_scale.compute(x), canvas.top + view.frame.y_scale.compute(y)];
}"""


def point(page: Page, x: float, y: float) -> tuple[float, float]:
    px, py = page.evaluate(POINT_JS, [x, y])
    return px, py


def test_bokeh_accessors_follow_real_gestures(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#selected")).to_have_text("None", timeout=30000)
    page.wait_for_function("() => window.Bokeh && window.Bokeh.index", timeout=30000)
    page.wait_for_timeout(500)

    # Tap the point (5, 5): reports the tap and selects row 1
    page.mouse.click(*point(page, 5, 5))
    expect(page.locator("#tapped")).to_have_text("5,5", timeout=5000)
    expect(page.locator("#selected")).to_have_text("[1]", timeout=5000)

    # Box-select around (5, 5) and (8, 8)
    start, end = point(page, 4, 9), point(page, 9, 4)
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(*end, steps=8)
    page.mouse.up()
    expect(page.locator("#selected_rows")).to_have_text("b,c", timeout=5000)

    # Wheel zoom reports the new ranges
    page.mouse.move(*point(page, 5, 5))
    page.mouse.wheel(0, -200)
    expect(page.locator("#zoomed")).to_have_text("zoomed", timeout=5000)

    assert_no_unexpected_errors(errors, failed_requests)
