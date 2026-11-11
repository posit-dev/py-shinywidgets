from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The demo volume is fetched from niivue.com by the browser
ALLOWED_REQUEST_FAILURES = ("niivue.com",)

FRAC_COORDS = re.compile(r"^-?\d+\.\d{3}(,-?\d+\.\d{3}){2}$")
# The trait default (volume center) -- a synced drag must move it off this
CENTER = "0.500,0.500,0.500"


def wait_for_sync(page: Page) -> None:
    """Wait until a crosshair drag made in the browser has reached the
    server, WITHOUT reading the accessor (an ungated accessor read would
    defeat the late-first-read scenario). The frontend's scene poll runs
    every 30 ms while the canvas is focused and the debounced location
    stream settles within 250 ms, and client->server messages are ordered,
    so once this delay has passed, the next message (the button click) is
    processed after the drag's updates."""
    page.wait_for_timeout(700)


def test_crosshair_drag_syncs_and_reaches_a_gated_first_read(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    canvas = page.locator("#brain canvas").first
    expect(canvas).to_be_visible(timeout=60000)
    # Await the volume load on a real signal (the widget's image_loaded
    # event), not a fixed timeout
    expect(page.locator("#loaded")).to_have_text("yes", timeout=120000)
    # Nothing reads the accessor until the button is clicked, so the gated
    # outputs are still empty
    expect(page.locator("#location")).to_have_text("")
    expect(page.locator("#trait")).to_have_text("")

    # Drag the crosshair off-center (the mousedown moves the crosshair; the
    # drag gesture is what drives the frontend's scene poll)
    box = canvas.bounding_box()
    assert box is not None
    x0 = box["x"] + box["width"] * 0.25
    y0 = box["y"] + box["height"] * 0.3
    page.mouse.move(x0, y0)
    page.mouse.down()
    page.mouse.move(x0 + 40, y0 + 30, steps=10)
    page.mouse.up()
    wait_for_sync(page)

    page.click("#read_location")
    # The drag synced the crosshair position to the Python-side trait under
    # shinywidgets' comm (moved off the volume-center default)
    expect(page.locator("#trait")).to_have_text(FRAC_COORDS, timeout=30000)
    trait = page.locator("#trait").inner_text()
    assert trait != CENTER, f"crosshair drag never synced to Python: {trait}"
    # And the gated first read reflects the drag (a full stream payload, not
    # the render-time seed of the volume center)
    expect(page.locator("#location")).to_have_text(
        re.compile(r"^stream:"), timeout=30000
    )

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_404s=ALLOWED_REQUEST_FAILURES
    )
