from __future__ import annotations

from playwright.sync_api import Page, expect


def test_ipyleaflet_marker_renders_on_first_click(page: Page, local_app) -> None:
    errors: list[str] = []

    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    map_locator = page.locator("#map .leaflet-container")
    expect(map_locator).to_have_count(1)

    marker_locator = page.locator("#map .leaflet-marker-icon")
    expect(marker_locator).to_have_count(0)

    map_locator.click(position={"x": 150, "y": 150})
    expect(marker_locator).to_have_count(1)

    map_locator.click(position={"x": 220, "y": 180})
    expect(marker_locator).to_have_count(2)

    lowered_errors = [err.lower() for err in errors]
    assert not any("state_change" in err for err in lowered_errors)
    assert not any("create_child_view" in err for err in lowered_errors)
    assert not any("couldn't handle message" in err for err in lowered_errors)
