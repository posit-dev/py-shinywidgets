from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.playwright.conftest import assert_no_browser_errors, collect_browser_errors


def assert_controls_stable(page: Page) -> None:
    expect(page.locator("#map .leaflet-control-layers")).to_have_count(1, timeout=5000)
    expect(page.locator("#map .leaflet-control-search")).to_have_count(1, timeout=5000)


def assert_route_visible(page: Page) -> None:
    expect(page.locator("#map .endpoint-marker")).to_have_count(2, timeout=5000)
    expect(
        page.locator("#map .leaflet-overlay-pane svg path.leaflet-interactive")
    ).to_have_count(1, timeout=5000)


def test_ipyleaflet_live_layer_updates(page: Page, local_app) -> None:
    errors = collect_browser_errors(page)

    page.goto(local_app.url)
    expect(page.locator("#map .leaflet-container")).to_have_count(1, timeout=30000)

    assert_controls_stable(page)
    assert_route_visible(page)

    page.click("#update_route")
    assert_controls_stable(page)
    assert_route_visible(page)

    page.click("#toggle_sample")
    expect(page.locator("#map .sample-point")).to_have_count(1, timeout=5000)
    assert_controls_stable(page)

    page.click("#toggle_sample")
    expect(page.locator("#map .sample-point")).to_have_count(0, timeout=5000)
    assert_controls_stable(page)

    assert_no_browser_errors(
        errors,
        [
            "create_child_view",
            "state_change",
            "widget is not attached",
            "no comm channel defined",
        ],
    )
