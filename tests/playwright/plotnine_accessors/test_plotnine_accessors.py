from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)

COORDS = re.compile(r"^-?\d+\.\d{2},-?\d+\.\d{2}$")
LIMITS = re.compile(r"^\(-?\d+\.\d{2},-?\d+\.\d{2}\),\(-?\d+\.\d{2},-?\d+\.\d{2}\)$")


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


def test_plotnine_limits_follow_a_toolbar_zoom(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#plot canvas").first).to_be_visible(timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#plot", timeout=30000)
    # Seeded from the rendered plot
    expect(page.locator("#limits")).to_have_text(LIMITS, timeout=30000)
    limits_before = page.locator("#limits").inner_text()

    # Activate the toolbar's zoom-to-rect mode and drag a rectangle
    zoom = page.locator("#plot [title^='Zoom to rectangle']")
    expect(zoom).to_be_visible(timeout=10000)
    zoom.click()
    box = page.locator("#plot canvas").first.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.6, steps=8
    )
    page.mouse.up()

    # limits update (after the 250 ms debounce)
    expect(page.locator("#limits")).not_to_have_text(limits_before, timeout=10000)
    expect(page.locator("#limits")).to_have_text(LIMITS, timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)
