from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)

COORDS = re.compile(r"^-?\d+\.\d{2},-?\d+\.\d{2}$")


def test_plotnine_clicked_reports_coordinates(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#plot canvas").first).to_be_visible(timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#plot", timeout=30000)
    expect(page.locator("#clicked")).to_have_text("None")

    # Click the center of the plot (regression-proofing the shared matplotlib
    # implementation against plotnine's drawn-copy coercion)
    box = page.locator("#plot canvas").first.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    expect(page.locator("#clicked")).to_have_text(COORDS, timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)
