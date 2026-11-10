from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    expose_manager,
)

# Each lonboard map bundles its own copy of luma.gl (see render_lonboard)
LUMA_REINIT = "luma.gl: This version of luma.gl has already been initialized"

# True once some browser model retains a pick on its `selected_index`
# attribute. lonboard's frontend sets it on the Backbone model on click and
# pushes it with save_changes(), so this is both the retained state the
# accessor seeds from and confirmation that a click actually picked a row:
# the canvas can be visible before the map accepts picks. Requires the
# expose_manager route.
PICK_RETAINED_JS = """async () => {
  const models = await Promise.all(
    Object.values(window.widgetManager._models).map((p) => p.catch(() => null))
  );
  return models
    .filter((m) => m)
    .some((m) => m.get('selected_index') !== null &&
                 m.get('selected_index') !== undefined);
}"""


def wait_for_sync(page: Page) -> None:
    """Wait until a pick made in the browser has reached the server, WITHOUT
    reading the accessor (an ungated accessor read would attach it early,
    defeating the late-first-read scenario). The frontend pushes the pick
    with save_changes() right after setting it, and client->server messages
    are ordered, so once the delay has passed, the next message (the button
    click) is processed after the pick."""
    page.wait_for_timeout(700)


def click_pick(page: Page, cx: float, cy: float) -> None:
    """Click the cluster, retrying until the pick is retained browser-side."""
    for _ in range(10):
        page.mouse.click(cx, cy)
        try:
            page.wait_for_function(PICK_RETAINED_JS, timeout=3000)
            return
        except PlaywrightTimeoutError:
            pass
    page.wait_for_function(PICK_RETAINED_JS, timeout=30000)


def test_pick_before_first_read_is_reported(page: Page, local_app) -> None:
    """A pick made before the accessor's (gated) first read is reflected in
    that read. Nothing in the app reads selected_index() before the button
    click, so the first read is genuinely late: pre-change (kind="event",
    lazy attach on first read) the pick below fired into a nonexistent
    listener and this read returned None.

    selected_index() is a kind="state" accessor: it attaches at render, so
    its observer on each layer's selected_index trait is in place before
    the browser can pick, and the pick is captured whether it precedes the
    first read (retained on the trait) or follows it (live sync).
    """
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    canvas = page.locator("#map .lonboard canvas").first
    expect(canvas).to_be_visible(timeout=30000)
    # Nothing reads the accessor until the button is clicked (any ungated
    # read would attach it early), so the gated output is still empty
    expect(page.locator("#picked")).to_have_text("")

    box = canvas.bounding_box()
    assert box is not None
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

    # Pick BEFORE the gated first read of selected_index(), and wait for the
    # pick to reach the server before clicking (see wait_for_sync)
    click_pick(page, cx, cy)
    wait_for_sync(page)

    page.locator("#read_pick").click()
    expect(page.locator("#picked")).to_have_text(re.compile(r"^[0-4]$"), timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests, allowed_errors=(LUMA_REINIT,))
