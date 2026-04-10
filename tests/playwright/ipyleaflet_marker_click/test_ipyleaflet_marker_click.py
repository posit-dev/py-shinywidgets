from __future__ import annotations

import time

from playwright.sync_api import Page, expect


def test_ipyleaflet_marker_renders_on_first_click(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    map_locator = page.locator(".leaflet-container")
    map_locator.wait_for(timeout=30000)
    time.sleep(1)

    map_bounds = map_locator.bounding_box()
    assert map_bounds is not None

    page.mouse.click(
        map_bounds["x"] + map_bounds["width"] / 2,
        map_bounds["y"] + map_bounds["height"] / 2,
    )

    expect(page.locator(".leaflet-marker-icon")).to_have_count(1, timeout=5000)
    assert not any("state_change" in err.lower() for err in errors)
