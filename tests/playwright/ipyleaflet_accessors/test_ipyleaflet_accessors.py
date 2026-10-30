from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_ipyleaflet_accessors_follow_gestures(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#map .leaflet-container")).to_have_count(1, timeout=30000)
    expect(page.locator("#leaf_map .leaflet-container")).to_have_count(
        1, timeout=30000
    )

    # Seeds: bounds cancels until the browser reports, then appears; zoom and
    # center read the constructor values
    expect(page.locator("#zoom")).to_have_text("4.0", timeout=30000)
    expect(page.locator("#center")).to_have_text("[52, 0]")
    expect(page.locator("#bounds")).not_to_have_text("", timeout=30000)
    expect(page.locator("#leaf_bounds")).not_to_have_text("", timeout=30000)
    bounds_before = page.locator("#bounds").inner_text()

    # Zoom-in control: bounds, zoom, and (leafmap) bounds all update
    page.locator("#map .leaflet-control-zoom-in").click()
    expect(page.locator("#zoom")).to_have_text("5.0", timeout=30000)
    expect(page.locator("#bounds")).not_to_have_text(bounds_before, timeout=30000)
    page.locator("#leaf_map .leaflet-control-zoom-in").click()
    leaf_before = page.locator("#leaf_bounds").inner_text()
    page.locator("#leaf_map .leaflet-control-zoom-in").click()
    expect(page.locator("#leaf_bounds")).not_to_have_text(leaf_before, timeout=30000)

    # Map click: [lat, lng] near the map's center (northern hemisphere, so a
    # lng/lat swap fails the assertion)
    page.locator("#map .leaflet-container").click(position={"x": 200, "y": 150})
    expect(page.locator("#clicked")).to_have_text(
        re.compile(r"^\[5[0-9]\.\d+, -?\d+(\.\d+)?\]$"), timeout=5000
    )

    # Draw a circlemarker with the DrawControl (the default control offers
    # polyline/polygon/circlemarker): drawn_features() grows to 1
    page.locator("#map .leaflet-draw-draw-circlemarker").click()
    page.locator("#map .leaflet-container").click(position={"x": 260, "y": 200})
    expect(page.locator("#features")).to_have_text("1", timeout=5000)
    assert_no_unexpected_errors(errors, failed_requests)
