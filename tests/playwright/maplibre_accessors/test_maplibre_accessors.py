from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

CANVAS = "#map canvas.maplibregl-canvas"
TIMEOUT = 60000

# mapbox-gl-draw's bundled line styles predate current MapLibre GL JS's
# stricter style validation, so its layers log a paint-property error (the
# draw outline is invisible, but drawing and the draw_* traits all work).
# Known upstream issue; see docs/widget-guides/maplibre/NOTES.md.
DRAW_STYLE_ERRORS = ("layers.gl-draw-lines",)

# anywidget evaluates a widget's inline ESM once per *view*, so the map
# after a re-render re-initializes luma.gl's page-global runtime; luma keeps
# the first initialization and logs this (benign) message for the rest (see
# KEPLERGL_ALLOWED_ERRORS in tests/playwright/conftest.py)
RERENDER_ALLOWED_ERRORS = DRAW_STYLE_ERRORS + (
    "luma.gl: This version of luma.gl has already been initialized",
)


def pan_map(page: Page) -> None:
    box = page.locator(CANVAS).bounding_box()
    assert box is not None
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 120, cy + 60, steps=10)
    page.mouse.up()


def click_map(page: Page, dx: int = 80, dy: int = 40) -> None:
    box = page.locator(CANVAS).bounding_box()
    assert box is not None
    page.mouse.click(
        box["x"] + box["width"] / 2 + dx, box["y"] + box["height"] / 2 + dy
    )


def test_view_state_reports_after_a_pan(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator(CANVAS)).to_be_visible(timeout=TIMEOUT)
    # Seeded from the map's load report (the render function's own center/zoom)
    expect(page.locator("#view_state_out")).to_have_text(
        "zoom=11.00 center=(2.352,48.857)", timeout=TIMEOUT
    )

    pan_map(page)
    # The browser reports on moveend, when the drag finishes
    expect(page.locator("#view_state_out")).not_to_have_text(
        "zoom=11.00 center=(2.352,48.857)", timeout=TIMEOUT
    )
    expect(page.locator("#view_state_out")).to_have_text(
        re.compile(r"zoom=11\.00 center=\(2\.\d+,48\.\d+\)"), timeout=TIMEOUT
    )

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=DRAW_STYLE_ERRORS
    )


def test_clicked_reports_and_survives_a_rerender(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator(CANVAS)).to_be_visible(timeout=TIMEOUT)
    expect(page.locator("#clicked_out")).to_have_text("none", timeout=TIMEOUT)

    click_map(page)
    expect(page.locator("#clicked_out")).to_have_text(
        re.compile(r"clicked=\(-?\d+\.\d+,-?\d+\.\d+\)"), timeout=TIMEOUT
    )
    kept = page.locator("#clicked_out").inner_text()

    # A re-render keeps the click until the user clicks the new map
    page.click("#rerender")
    expect(page.locator(CANVAS)).to_be_visible(timeout=TIMEOUT)
    page.wait_for_timeout(3000)  # let the new map finish loading
    expect(page.locator("#clicked_out")).to_have_text(kept)

    click_map(page, dx=-100, dy=-60)
    expect(page.locator("#clicked_out")).not_to_have_text(kept, timeout=TIMEOUT)

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=RERENDER_ALLOWED_ERRORS
    )


def test_drawn_features_follow_mapbox_draw_and_reset_on_rerender(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator(CANVAS)).to_be_visible(timeout=TIMEOUT)
    expect(page.locator("#drawn_out")).to_have_text("0 feature(s)", timeout=TIMEOUT)

    # Draw a triangle with the polygon tool: three clicks, Enter to finish
    page.locator(".mapbox-gl-draw_polygon").click()
    box = page.locator(CANVAS).bounding_box()
    assert box is not None
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.click(cx - 100, cy - 60)
    page.mouse.click(cx + 100, cy - 60)
    page.mouse.click(cx, cy + 80)
    page.keyboard.press("Enter")
    expect(page.locator("#drawn_out")).to_have_text("1 feature(s)", timeout=TIMEOUT)

    # Drawn shapes live on the map, so a re-render starts from the new map's
    # empty set
    page.click("#rerender")
    expect(page.locator("#drawn_out")).to_have_text("0 feature(s)", timeout=TIMEOUT)

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=RERENDER_ALLOWED_ERRORS
    )
