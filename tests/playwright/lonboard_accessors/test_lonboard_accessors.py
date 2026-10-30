from __future__ import annotations

import ast
import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Each lonboard map bundles its own copy of luma.gl (see render_lonboard)
LUMA_REINIT = "luma.gl: This version of luma.gl has already been initialized"


def test_lonboard_accessors_follow_gestures(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    canvas = page.locator("#map .lonboard canvas").first
    expect(canvas).to_be_visible(timeout=30000)
    expect(page.locator("#picked")).to_have_text("None")
    expect(page.locator("#bbox")).to_have_text("None")

    box = canvas.bounding_box()
    assert box is not None
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

    # Click on the cluster: clicked() reports (lng, lat) and selected_index()
    # picks a row. The map is centered on (20, 40), so the distinct
    # magnitudes catch a lat/lng swap.
    page.mouse.click(cx, cy)
    expect(page.locator("#picked")).to_have_text(re.compile(r"^[0-4]$"), timeout=5000)
    lng, lat = ast.literal_eval(page.locator("#clicked").inner_text())
    assert 15 < lng < 25 and 35 < lat < 45, (lng, lat)

    # Pan: view_state settles ~300 ms after the gesture
    before = page.locator("#view_state").inner_text()
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 120, cy + 80, steps=8)
    page.mouse.up()
    expect(page.locator("#view_state")).not_to_have_text(before, timeout=5000)

    # Select BBox: the bbox button, then click the two corners (lonboard's
    # bbox selection is click-click, not a drag)
    page.locator('#map button[aria-label="Select BBox"]').click()
    page.mouse.click(cx - 100, cy - 60)
    page.mouse.click(cx + 100, cy + 60)
    expect(page.locator("#bbox")).not_to_have_text("None", timeout=5000)
    # (minx, miny, maxx, maxy), i.e. (west, south, east, north)
    minx, miny, maxx, maxy = ast.literal_eval(page.locator("#bbox").inner_text())
    assert minx < maxx and miny < maxy, (minx, miny, maxx, maxy)

    assert_no_unexpected_errors(errors, failed_requests, allowed_errors=(LUMA_REINIT,))
