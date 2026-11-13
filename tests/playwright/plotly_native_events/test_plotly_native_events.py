from __future__ import annotations

from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Page coordinates of a data point, via plotly.js's axis conversions (same
# helper as tests/playwright/plotly_accessors).
POINT_JS = """([id, x, y]) => {
  const gd = document.querySelector(`#${id} .js-plotly-plot`);
  const L = gd._fullLayout;
  const box = gd.querySelector(".nsewdrag").getBoundingClientRect();
  return [box.left + L.xaxis.d2p(x), box.top + L.yaxis.d2p(y)];
}"""

# True once the plot holds a selection, i.e. the drag gesture landed (see
# tests/playwright/plotly_selection_seed).
SELECTED_STATE_JS = """(id) => {
  const gd = document.querySelector(`#${id} .js-plotly-plot`);
  if (!gd || !gd._fullLayout) return false;
  return (gd.data || []).some(
    (t) => Array.isArray(t.selectedpoints) && t.selectedpoints.length > 0
  );
}"""


def point(page: Page, x: float, y: float, id: str) -> tuple[float, float]:
    px, py = page.evaluate(POINT_JS, [id, x, y])
    return px, py


def box_select(page: Page, id: str) -> None:
    """Box-select the points with x in [1.5, 3.5] (indices 1 and 2),
    retrying until the selection lands on the graph div."""
    for _ in range(10):
        start, end = point(page, 1.5, 12, id=id), point(page, 3.5, 0, id=id)
        page.mouse.move(*start)
        page.mouse.down()
        page.mouse.move((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, steps=5)
        page.mouse.move(*end, steps=5)
        page.mouse.up()
        try:
            page.wait_for_function(SELECTED_STATE_JS, arg=id, timeout=3000)
            return
        except PlaywrightTimeoutError:
            pass
    page.wait_for_function(SELECTED_STATE_JS, arg=id, timeout=30000)


def test_native_plotly_events_need_listen_to_native(page: Page, local_app) -> None:
    """#479: plotly.py's own per-point report of clicks, hovers and
    selections is muted by default; listen_to=["native"] restores it for
    callbacks registered after the render and for Python-side
    `selectedpoints`."""
    errors, failed_requests = collect_errors(page)
    frames: list[str] = []

    def on_ws(ws) -> None:  # noqa: ANN001
        ws.on("framesent", lambda payload: frames.append(payload))

    page.on("websocket", on_ws)
    page.goto(local_app.url)
    for id in ("native", "default"):
        expect(page.locator(f"#{id} .js-plotly-plot")).to_be_visible(timeout=60000)
    expect(page.locator("#from_callback")).to_have_text("None", timeout=30000)

    # The default output first: messages reach the server in order, so by the
    # time the native output's selection (made after it) has arrived, a
    # report from the default output would have too.
    box_select(page, "default")
    box_select(page, "native")
    expect(page.locator("#from_callback")).to_have_text("1,2", timeout=30000)

    page.locator("#read").click()
    expect(page.locator("#selectedpoints")).to_have_text(
        "native=1,2 default=None", timeout=30000
    )

    assert [f for f in frames if "_js2py_pointsCallback" in f]

    assert_no_unexpected_errors(errors, failed_requests)
