from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_maplibre_renders_canvas(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # maplibre's MapWidget is WebGL (pixels aren't readable via getImageData),
    # so assert its canvas exists and has non-zero dimensions
    canvas = page.locator("#map canvas.maplibregl-canvas")
    expect(canvas).to_have_count(1, timeout=30000)
    box = canvas.bounding_box()
    assert box is not None and box["width"] > 0 and box["height"] > 0

    assert_no_unexpected_errors(errors, failed_requests)


def test_maplibre_click_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # The map's `clicked` trait starts empty; clicking the map should sync it
    # back to Python (browser -> shinywidgets comm -> reactive_read -> UI)
    expect(page.locator("#map_clicked")).to_have_text("{}", timeout=30000)
    page.locator("#map canvas.maplibregl-canvas").click()
    expect(page.locator("#map_clicked")).to_contain_text("lng", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_maplibre_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#map .maplibregl-map")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    # Re-rendering replaces the widget, but the old view must be disposed
    # (i.e., no accumulation of maps)
    expect(page.locator("#map .maplibregl-map")).to_have_count(1)

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
