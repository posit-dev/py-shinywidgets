from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

POINT_JS = """([x, y]) => {
  const gd = document.querySelector("#plot .js-plotly-plot");
  const L = gd._fullLayout;
  const box = gd.querySelector(".nsewdrag").getBoundingClientRect();
  return [box.left + L.xaxis.d2p(x), box.top + L.yaxis.d2p(y)];
}"""


def drag_select(page: Page, x0: float, x1: float) -> None:
    start = page.evaluate(POINT_JS, [x0, 26])
    end = page.evaluate(POINT_JS, [x1, 0])
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(*end, steps=8)
    page.mouse.up()


def test_selection_reaches_a_reader_from_the_first_flush_and_after_rerender(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#plot .js-plotly-plot")).to_have_count(1, timeout=30000)
    page.wait_for_timeout(500)

    drag_select(page, 1.5, 3.5)
    expect(page.locator("#selected_rows")).to_have_text("2,3", timeout=5000)

    old = page.locator("#plot .js-plotly-plot").element_handle()
    page.click("#rerender")
    page.wait_for_function("(el) => !el.isConnected", arg=old, timeout=10000)
    expect(page.locator("#plot .js-plotly-plot")).to_have_count(1, timeout=10000)
    expect(page.locator("#selected_rows")).to_have_text("")
    page.wait_for_timeout(500)

    drag_select(page, 3.5, 5.5)
    expect(page.locator("#selected_rows")).to_have_text("4,5", timeout=5000)
    assert_no_unexpected_errors(errors, failed_requests)
