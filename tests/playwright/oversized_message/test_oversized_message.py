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

SELECTED_STATE_JS = """(id) => {
  const gd = document.querySelector(`#${id} .js-plotly-plot`);
  if (!gd || !gd._fullLayout) return false;
  return (gd.data || []).some(
    (t) => Array.isArray(t.selectedpoints) && t.selectedpoints.length > 0
  );
}"""


def point(page: Page, x: float, y: float, id: str = "plot") -> tuple[float, float]:
    px, py = page.evaluate(POINT_JS, [id, x, y])
    return px, py


def lasso_center(page: Page, id: str = "plot") -> None:
    """Lasso the center of the cloud (most of its 300K points): a closed
    rectangular path around (0, 0), retried until the selection lands."""
    corners = [(-1, 1), (1, 1), (1, -1), (-1, -1), (-1, 1)]
    for _ in range(10):
        pts = [point(page, x, y, id=id) for x, y in corners]
        page.mouse.move(*pts[0])
        page.mouse.down()
        for p in pts[1:]:
            page.mouse.move(*p, steps=5)
        page.mouse.up()
        try:
            page.wait_for_function(SELECTED_STATE_JS, arg=id, timeout=3000)
            return
        except PlaywrightTimeoutError:
            pass
    page.wait_for_function(SELECTED_STATE_JS, arg=id, timeout=30000)


def test_oversized_message_is_dropped_not_disconnected(page: Page, local_app) -> None:
    """A selection message over the (here tiny) limit is dropped client-side
    with an actionable console error; the session keeps working."""
    errors, failed_requests = collect_errors(page)
    dropped: list[str] = []
    page.on(
        "console",
        lambda msg: dropped.append(msg.text) if "dropped a" in msg.text else None,
    )
    page.goto(local_app.url)
    expect(page.locator("#plot .js-plotly-plot")).to_be_visible(timeout=60000)

    lasso_center(page)

    # The guard logs the drop (with the --ws-max-size workaround) instead of
    # letting the message close the websocket
    for _ in range(60):
        if dropped and "--ws-max-size" in dropped[0]:
            break
        page.wait_for_timeout(500)
    assert dropped, "expected a 'dropped a ... MB message' console error"
    assert "--ws-max-size" in dropped[0]

    # The session is still alive: no disconnect overlay, and the app still
    # responds to the server round-trip
    expect(page.locator("#shiny-disconnected-overlay")).to_have_count(0)
    expect(page.locator("#heartbeat")).to_have_text("alive")
    assert page.evaluate("() => 1 + 1") == 2

    assert_no_unexpected_errors(errors, failed_requests, allowed_errors=("dropped a",))
