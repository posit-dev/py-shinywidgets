from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

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


def click_until_bound(
    page: Page, x: float, y: float, id: str, out: str, text: str
) -> None:
    # The click listener binds only once Python's bind request reaches the
    # plot, which can take a while under load, so click until one lands
    for _ in range(20):
        page.mouse.click(*point(page, x, y, id=id))
        try:
            expect(page.locator(f"#{out}")).to_have_text(text, timeout=500)
            return
        except AssertionError:
            pass
    expect(page.locator(f"#{out}")).to_have_text(text)


def drag(page: Page, start: tuple[float, float], end: tuple[float, float]) -> None:
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, steps=5)
    page.mouse.move(*end, steps=5)
    page.mouse.up()


def test_plotly_accessors_follow_real_gestures(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#plot .js-plotly-plot")).to_have_count(1, timeout=30000)
    expect(page.locator("#clicked")).to_have_text("None", timeout=10000)
    expect(page.locator("#selected_rows")).to_have_text("")

    # Click the point (3, 9): the first point of trace 1 (group "b")
    click_until_bound(page, 3, 9, id="plot", out="clicked", text="1,0,3,9")

    # Box-select x in [1.5, 4.5]: rows 1, 2, 3 of df, across both traces
    drag(page, point(page, 1.5, 26), point(page, 4.5, 0))
    expect(page.locator("#selected_rows")).to_have_text("2,3,4", timeout=5000)
    expect(page.locator("#brushed")).to_have_text("range", timeout=5000)

    # Double-click clears the selection, the brush, and the click
    page.mouse.dblclick(*point(page, 1, 25))
    expect(page.locator("#selected_rows")).to_have_text("", timeout=5000)
    expect(page.locator("#brushed")).to_have_text("None")
    expect(page.locator("#clicked")).to_have_text("None")

    # Zooming reports axis ranges, and only those
    page.evaluate(
        """() => window.Plotly.relayout(
            document.querySelector("#plot .js-plotly-plot"),
            {"xaxis.range": [0, 6], "dragmode": "zoom"})"""
    )
    expect(page.locator("#relayout")).to_have_text("xaxis.range", timeout=5000)

    # In-place updates keep the bindings
    page.click("#restyle")
    page.wait_for_timeout(500)
    page.mouse.click(*point(page, 4, 16))
    expect(page.locator("#clicked")).to_have_text("1,1,4,16", timeout=5000)

    # An accessor first read after render still gets its events (debounced)
    page.click("#late")
    expect(page.locator("#brushing")).to_have_text("None", timeout=5000)
    page.wait_for_timeout(300)
    page.evaluate(
        """() => window.Plotly.relayout(
            document.querySelector("#plot .js-plotly-plot"), {"dragmode": "select"})"""
    )
    drag(page, point(page, 0.5, 26), point(page, 2.5, 0))
    expect(page.locator("#brushing")).to_have_text("range", timeout=5000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_plotly_accessors_on_an_app_defined_figure_subclass(
    page: Page, local_app
) -> None:
    page.goto(local_app.url)
    # A still-hidden (pre-reveal) graph can't receive mouse events, so wait
    # for the reveal, not just the element
    expect(page.locator("#sub_plot .js-plotly-plot")).to_be_visible(timeout=30000)
    expect(page.locator("#sub_clicked")).to_have_text("None", timeout=10000)

    page.locator("#sub_plot").scroll_into_view_if_needed()
    click_until_bound(page, 3, 9, id="sub_plot", out="sub_clicked", text="3")
