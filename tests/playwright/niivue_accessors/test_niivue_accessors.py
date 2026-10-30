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
    page.wait_for_timeout(3000)  # let the remote volume finish loading

    # Click the canvas: the crosshair moves there and the location reports
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    expect(page.locator("#location")).to_have_text(MM_COORDS, timeout=30000)

    # Drag the crosshair: reports stream in, but the debounced accessor
    # settles without a flush storm (mirrors accessor_helper's debounce
    # assertion)
    expect(page.locator("#location")).to_have_text(MM_COORDS)
    before = int(page.locator("#eval_count").inner_text())
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] / 2 + 80, box["y"] + box["height"] / 2 + 40, steps=15
    )
    page.wait_for_timeout(1000)
    page.mouse.up()
    expect(page.locator("#eval_count")).not_to_have_text(str(before), timeout=10000)
    page.wait_for_timeout(750)  # let the debounce window close
    n = int(page.locator("#eval_count").inner_text()) - before
    assert 1 <= n <= 4, f"expected a small bounded number of evaluations, got {n}"

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_404s=ALLOWED_REQUEST_FAILURES
    )
