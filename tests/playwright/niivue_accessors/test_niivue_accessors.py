from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

MM_COORDS = re.compile(r"^-?\d+\.\d(,-?\d+\.\d){2,3}$")

# The demo volume is fetched from niivue.com by the browser
ALLOWED_REQUEST_FAILURES = ("niivue.com",)


def test_location_reports_crosshair_and_debounces(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    canvas = page.locator("#brain canvas").first
    expect(canvas).to_be_visible(timeout=60000)
    expect(page.locator("#location")).to_have_text("None", timeout=30000)
    # Await the volume load on a real signal (the widget's image_loaded
    # event), not a fixed timeout
    expect(page.locator("#loaded")).to_have_text("yes", timeout=120000)

    # Click the canvas: the crosshair moves there and the location reports
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    expect(page.locator("#location")).to_have_text(MM_COORDS, timeout=30000)

    # A burst of 20 crosshair events in a tight loop must coalesce into a
    # single debounced publish (the accessor debounces by 250 ms by default).
    # The assertion counts PUBLISHES, not evaluations: the events arrive
    # synchronously, so without rate limiting their publishes would still
    # batch into one flush (one evaluation) -- publish counting is what
    # actually detects a lost debounce. A synthetic burst keeps the event
    # pacing deterministic (a real drag's pacing made this flaky in CI).
    expect(page.locator("#publish_count")).to_have_text(
        re.compile(r"^\d+$"), timeout=10000
    )
    before = int(page.locator("#publish_count").inner_text())
    page.click("#burst")
    # The settled value is the burst's final event -- which only appears once
    # the (debounced) publish has happened, so the count is final by now
    expect(page.locator("#location")).to_have_text("19.0,0.0,0.0", timeout=10000)
    after = int(page.locator("#publish_count").inner_text())
    assert after - before == 1, (
        f"20 crosshair events caused {after - before} publishes; "
        "the 250 ms debounce should coalesce them into 1"
    )

    # A real crosshair drag still settles on a correct location
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] / 2 + 80, box["y"] + box["height"] / 2 + 40, steps=15
    )
    page.mouse.up()
    expect(page.locator("#location")).to_have_text(MM_COORDS, timeout=10000)

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_404s=ALLOWED_REQUEST_FAILURES
    )
