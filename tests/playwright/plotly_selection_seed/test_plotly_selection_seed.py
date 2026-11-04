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

# True once the plot holds a selection (trace selectedpoints is also where
# the bridge's seed reads it from). Confirms a drag gesture actually landed:
# the plot can be visible before it accepts drags.
SELECTED_STATE_JS = """(id) => {
  const gd = document.querySelector(`#${id} .js-plotly-plot`);
  if (!gd || !gd._fullLayout) return false;
  return (gd.data || []).some(
    (t) => Array.isArray(t.selectedpoints) && t.selectedpoints.length > 0
  );
}"""

DESELECTED_STATE_JS = SELECTED_STATE_JS.replace("return (", "return !(")


def wait_for_sync(page: Page) -> None:
    """Wait until a selection/deselection made in the browser has reached
    the server, WITHOUT reading an accessor (an ungated accessor read would
    attach it early, defeating the late-first-read scenario). plotly.js
    emits plotly_selected a few hundred ms after mouseup (held back for
    double-click disambiguation), and client->server messages are ordered,
    so once the delay has passed, the next message (the button click) is
    processed after the selection message."""
    page.wait_for_timeout(700)


def point(page: Page, x: float, y: float, id: str = "plot") -> tuple[float, float]:
    px, py = page.evaluate(POINT_JS, [id, x, y])
    return px, py


def drag(page: Page, start: tuple[float, float], end: tuple[float, float]) -> None:
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, steps=5)
    page.mouse.move(*end, steps=5)
    page.mouse.up()


# The three points of df with x in [1.5, 4.5]: trace 0's point 1 and trace
# 1's points 0 and 1 (df rows 1, 2, 3)
SELECTED_POINTS = "0,1;1,0;1,1"
SELECTED_ROWS = "2,3,4"
SELECTED_COUNT = "3"


def box_select(page: Page, id: str = "plot") -> None:
    """Box-select the points with x in [1.5, 4.5], retrying until the
    selection lands on the graph div."""
    for _ in range(10):
        drag(page, point(page, 1.5, 26, id=id), point(page, 4.5, 0, id=id))
        try:
            page.wait_for_function(SELECTED_STATE_JS, arg=id, timeout=3000)
            return
        except PlaywrightTimeoutError:
            pass
    page.wait_for_function(SELECTED_STATE_JS, arg=id, timeout=30000)


def goto_plot(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#plot .js-plotly-plot")).to_be_visible(timeout=30000)
    # Nothing reads the accessors until the button is clicked (any ungated
    # read would attach them early), so the gated outputs are still empty
    expect(page.locator("#selected")).to_have_text("")
    expect(page.locator("#selected_rows")).to_have_text("")
    expect(page.locator("#brushed")).to_have_text("")


def test_selection_before_first_read_is_reported(page: Page, local_app) -> None:
    """A box selection made before the accessor's (gated) first read is
    reflected in that read. Nothing in the app reads the accessors before
    the button click, so the first read is genuinely late: pre-change
    (kind="event", lazy attach on first read) the selection below fired
    into a nonexistent listener and this read returned None.

    selected()/brushed() are kind="state" accessors: they attach at render,
    and the bridge seeds the plot's current selection when the bind reaches
    the browser (js/src/plotly.ts), so the selection is captured whether it
    preceded the bind (seed) or followed it (live forwarding).
    """
    errors, failed_requests = collect_errors(page)
    goto_plot(page, local_app)

    # Select BEFORE the gated first read of selected()/selected_rows()/
    # brushed(), and wait for the selection to reach the server before
    # clicking (see wait_for_sync)
    box_select(page)
    wait_for_sync(page)

    page.locator("#read_selection").click()
    expect(page.locator("#selected")).to_have_text(SELECTED_POINTS, timeout=30000)
    expect(page.locator("#selected_rows")).to_have_text(SELECTED_ROWS)
    expect(page.locator("#brushed")).to_have_text("range")

    assert_no_unexpected_errors(errors, failed_requests)


def test_deselect_after_read_clears_selection(page: Page, local_app) -> None:
    """A deselect (double-click on the plot background) after the gated read
    clears the accessors: a re-read reports no selection."""
    errors, failed_requests = collect_errors(page)
    goto_plot(page, local_app)

    box_select(page)
    wait_for_sync(page)
    page.locator("#read_selection").click()
    expect(page.locator("#selected")).to_have_text(SELECTED_POINTS, timeout=30000)
    expect(page.locator("#brushed")).to_have_text("range")

    # Double-click the plot background (x=1, y=25 is no data point), wait
    # for the deselect to reach the server, then re-read: cleared
    page.mouse.dblclick(*point(page, 1, 25))
    page.wait_for_function(DESELECTED_STATE_JS, arg="plot", timeout=30000)
    wait_for_sync(page)

    page.locator("#read_selection").click()
    expect(page.locator("#selected")).to_have_text("None", timeout=30000)
    expect(page.locator("#selected_rows")).to_have_text("")
    expect(page.locator("#brushed")).to_have_text("None")

    assert_no_unexpected_errors(errors, failed_requests)
