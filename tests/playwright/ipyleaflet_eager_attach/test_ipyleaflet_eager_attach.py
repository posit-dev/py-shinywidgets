from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# A [lat, lng] near the map's center (northern hemisphere), as reported by
# clicked(); same assertion as tests/playwright/ipyleaflet_accessors
CLICK_COORDS = re.compile(r"^\[5[0-9]\.\d+, -?\d+(\.\d+)?\]$")


def goto_map(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#map .leaflet-container")).to_have_count(1, timeout=30000)
    # Nothing reads the accessors until a button is clicked
    expect(page.locator("#zoom")).to_have_text("")
    expect(page.locator("#clicked")).to_have_text("")


def test_state_accessor_captures_gesture_before_first_read(
    page: Page, local_app
) -> None:
    """Scenario-contract guard for state-kind accessors: a gesture made
    before the accessor's (gated) first read is reflected in that read.

    NOTE: this passes both pre- and post-#412 (verified by flipping
    AccessorSpec.eager's default back to False). ipyleaflet pushes its
    synced traits (zoom, bounds, ...) to Python unconditionally, and the
    pre-#412 lazy attach-on-first-read seeded the current -- already
    post-gesture -- value, so the read self-healed. Post-#412 the guarantee
    comes from the eager attach at render time instead of trait-sync luck:
    if a frontend ever gates its state sync on a Python-side listener, this
    test catches it. The eager/lazy attach timing itself is covered by unit
    tests (tests/unit/test_accessors.py).
    """
    errors, failed_requests = collect_errors(page)
    goto_map(page, local_app)

    # Zoom in BEFORE anything reads zoom(): the button below gates the
    # accessor's first read. Wait for the gesture to reach the server (the
    # sentinel output follows the raw trait) before triggering the read.
    page.locator("#map .leaflet-control-zoom-in").click()
    expect(page.locator("#synced_zoom")).to_have_text("5.0", timeout=30000)

    page.locator("#read_zoom").click()
    expect(page.locator("#zoom")).to_have_text("5.0", timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_event_accessor_misses_click_before_first_read(page: Page, local_app) -> None:
    """CHARACTERIZATION of current (documented) behavior, not the desired
    end state: kind="event" accessors still attach lazily, on first read, so
    an event that fires before the first read is missed.

    clicked() is read for the first time only after #read_clicked, so the
    map click made before the button click is lost. (To capture early
    events, an app warms the accessor up by reading it once, unconditionally,
    at startup -- see the AccessorSpec.eager docstring.)
    """
    errors, failed_requests = collect_errors(page)
    goto_map(page, local_app)

    # Click the map BEFORE anything reads clicked()
    page.locator("#map .leaflet-container").click(position={"x": 200, "y": 150})

    # The gated first read attaches the listener only now: the click above
    # is missed
    page.locator("#read_clicked").click()
    expect(page.locator("#clicked")).to_have_text("", timeout=10000)

    # ...but once attached, later clicks are captured
    page.locator("#map .leaflet-container").click(position={"x": 200, "y": 150})
    page.locator("#read_clicked").click()
    expect(page.locator("#clicked")).to_have_text(CLICK_COORDS, timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)
