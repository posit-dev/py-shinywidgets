from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
)

# Page coordinates of a data point, via plotly.js's axis conversions.
POINT_JS = """([id, x, y]) => {
  const gd = document.querySelector(`#${id} .js-plotly-plot`);
  const L = gd._fullLayout;
  const box = gd.querySelector(".nsewdrag").getBoundingClientRect();
  return [box.left + L.xaxis.d2p(x), box.top + L.yaxis.d2p(y)];
}"""


def point(page: Page, x: float, y: float, id: str = "plot") -> tuple[float, float]:
    px, py = page.evaluate(POINT_JS, [id, x, y])
    return px, py


def test_clicked_feedback_rerender_settles(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#plot .js-plotly-plot")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("1", timeout=10000)

    # Click the marker (3, 9). The click listener binds only once Python's
    # bind request reaches the plot, so click until one lands (which sets off
    # the feedback render), as in plotly_accessors. The landing replaces the
    # plot, so a retry may catch it mid-re-render.
    for _ in range(60):
        try:
            page.mouse.click(*point(page, 3, 9))
        except PlaywrightError:
            pass
        try:
            expect(page.locator("#render_count")).to_have_text("2", timeout=500)
            break
        except AssertionError:
            pass
    expect(page.locator("#render_count")).to_have_text("2")

    # The feedback render added the vline at the clicked x (the count updates
    # before the replacement plot finishes drawing, so poll for it)
    page.wait_for_function(
        """() => {
          const gd = document.querySelector('#plot .js-plotly-plot');
          return gd && gd._fullLayout && gd._fullLayout.shapes.length === 1;
        }""",
        timeout=10000,
    )

    # The render settles instead of looping (with the loop, one click kept
    # re-rendering at ~11 renders/s and never settled)
    count = page.locator("#render_count").inner_text()
    page.wait_for_timeout(2000)
    assert page.locator("#render_count").inner_text() == count
    assert int(count) <= 4

    assert_no_unexpected_errors(errors, failed_requests)
