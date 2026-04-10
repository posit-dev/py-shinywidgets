from __future__ import annotations

from playwright.sync_api import Page

MARKER_SELECTOR = "#plot .leaflet-overlay-pane path.leaflet-interactive"
MAP_SELECTOR = "#plot .leaflet-container"
TILE_SELECTOR = "#plot .leaflet-tile-loaded"


def wait_for_map(page: Page) -> None:
    page.wait_for_selector(MAP_SELECTOR, timeout=60000)
    page.wait_for_function(
        "() => document.querySelectorAll('#plot .leaflet-container').length === 1"
    )
    page.wait_for_function(
        "() => document.querySelectorAll('#plot .leaflet-tile-loaded').length > 0"
    )
    page.wait_for_function(
        "() => document.querySelectorAll('#plot .leaflet-overlay-pane path.leaflet-interactive').length >= 600"
    )


def test_ipyleaflet_rerender_keeps_map_alive_without_teardown_errors(
    page: Page, local_app
) -> None:
    errors: list[str] = []

    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    wait_for_map(page)

    for _ in range(8):
        page.click("#rerender")
        page.wait_for_timeout(50)

    wait_for_map(page)

    assert page.locator(MAP_SELECTOR).count() == 1
    assert page.locator(TILE_SELECTOR).count() > 0
    assert page.locator(MARKER_SELECTOR).count() >= 600

    blocked = (
        "widget is not attached",
        "state_change",
        "t is undefined",
        "cannot read properties of undefined",
    )
    lower_errors = [err.lower() for err in errors]
    assert not any(
        any(snippet in err for snippet in blocked) for err in lower_errors
    ), errors
