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

# True once the plot holds a selection (trace selectedpoints), i.e. the
# lasso gesture landed (see tests/playwright/plotly_selection_seed).
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


def test_region_only_selection_stays_small_and_connected(page: Page, local_app) -> None:
    """#459: reading only brushed() must not send per-point selection
    messages over shinywidgets' bridge, so lassoing a 300K-point cloud
    can't disconnect the session."""
    errors, failed_requests = collect_errors(page)
    frames: list[str] = []

    def on_ws(ws) -> None:  # noqa: ANN001
        ws.on("framesent", lambda payload: frames.append(payload))

    page.on("websocket", on_ws)
    page.goto(local_app.url)
    expect(page.locator("#plot .js-plotly-plot")).to_be_visible(timeout=60000)
    expect(page.locator("#brushed")).to_have_text("None", timeout=30000)

    lasso_center(page)
    expect(page.locator("#brushed")).to_contain_text("lassoPoints", timeout=30000)

    # shinywidgets' bridge messages (the region report among them) all stay
    # small: no per-point payload was requested, so none was sent (a slim
    # point is ~40 bytes, so 300K points would be >10 MB). plotly.py's own
    # `_js2py_pointsCallback` channel does still send the full selection --
    # shinywidgets can't gate it -- so only bridge frames are measured.
    bridge_frames = [
        f.replace('\\"', '"')
        for f in frames
        if '"shinywidgets"' in f.replace('\\"', '"')
    ]
    assert bridge_frames, "expected the bridge's region report"
    assert max(len(f) for f in bridge_frames) < 100_000
    # The session is still alive: no disconnect overlay
    expect(page.locator("#shiny-disconnected-overlay")).to_have_count(0)

    assert_no_unexpected_errors(errors, failed_requests)
