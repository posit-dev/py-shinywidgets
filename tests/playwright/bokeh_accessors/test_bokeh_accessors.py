from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Page coordinates of a data point, via the plot view's scales. The view is
# found by its output container: Bokeh.index order shifts when a plot
# re-renders (the new view is appended)
POINT_JS = """([x, y, outputId]) => {
  const views = [...window.Bokeh.index.values ? window.Bokeh.index.values() : Object.values(window.Bokeh.index)];
  const container = document.getElementById(outputId);
  const view = views.filter((v) => v.canvas_view && v.canvas_view.el.isConnected && container.contains(v.el))[0];
  const canvas = view.canvas_view.el.getBoundingClientRect();
  return [canvas.left + view.frame.x_scale.compute(x), canvas.top + view.frame.y_scale.compute(y)];
}"""


def point(page: Page, x: float, y: float, output: str = "plot") -> tuple[float, float]:
    px, py = page.evaluate(POINT_JS, [x, y, output])
    return px, py


def test_bokeh_accessors_follow_real_gestures(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    # selected() is a state accessor seeded at render: empty selection is []
    expect(page.locator("#selected")).to_have_text("[]", timeout=30000)
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

    # Tap the line's first segment (from (1,1) to (2,4)): bokeh reports a
    # line hit as line_indices, not indices (#472)
    page.mouse.click(*point(page, 1.5, 2.5, output="line_plot"))
    expect(page.locator("#line_selected")).to_have_text("[0]", timeout=5000)

    # Wheel zoom reports the new ranges
    page.mouse.move(*point(page, 5, 5))
    page.mouse.wheel(0, -200)
    expect(page.locator("#zoomed")).to_have_text("zoomed", timeout=5000)

    # After a re-render, the last tap is retained (it still happened), and
    # new taps still reach the accessor
    page.click("#rerender")
    page.wait_for_timeout(1000)
    expect(page.locator("#tapped")).to_have_text("5,5", timeout=10000)
    page.mouse.click(*point(page, 8, 8))
    expect(page.locator("#tapped")).to_have_text("8,8", timeout=5000)

    assert_no_unexpected_errors(errors, failed_requests)
