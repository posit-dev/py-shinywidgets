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


def lasso(page: Page, corners: list[tuple[float, float]], id: str = "plot") -> None:
    """Draw a closed lasso path through `corners` (data coordinates),
    retried until the selection lands."""
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


def lasso_center(page: Page, id: str = "plot") -> None:
    """Lasso the center of the cloud (most of its 300K points): a closed
    rectangular path around (0, 0)."""
    lasso(page, [(-1, 1), (1, 1), (1, -1), (-1, -1), (-1, 1)], id=id)


def test_oversized_message_is_dropped_not_disconnected(page: Page, local_app) -> None:
    """A selection message over the (here tiny) limit is dropped client-side
    with an actionable console error; the session keeps working."""
    errors, failed_requests = collect_errors(page)
    dropped: list[str] = []
    frames: list[str] = []
    page.on(
        "console",
        lambda msg: dropped.append(msg.text) if "dropped a" in msg.text else None,
    )

    def on_ws(ws) -> None:  # noqa: ANN001
        ws.on("framesent", lambda payload: frames.append(payload))

    page.on("websocket", on_ws)
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

    # The oversized messages were actually dropped, not just logged: neither
    # the bridge's selection event nor plotly.py's own points callback ever
    # reached the server (a log-but-send bug would pass the checks above,
    # since only the client-side limit is tiny)
    # No frame over the 64 KB limit was sent (the bind-time seed's tiny
    # `plotly_selected` frame and other small messages are fine; the fat
    # ones were dropped)
    assert frames, "expected some client->server frames"
    assert max(len(f) for f in frames) < 65_536

    # The session is still alive: no disconnect overlay
    expect(page.locator("#shiny-disconnected-overlay")).to_have_count(0)

    # ...and the widget channel still works after the drop: a small
    # selection (a corner patch, far under the limit) reaches Python
    lasso(page, [(2, 2.6), (3, 2.6), (3, 3.2), (2, 3.2), (2, 2.6)])
    expect(page.locator("#selected")).not_to_have_text("None", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests, allowed_errors=("dropped a",))
