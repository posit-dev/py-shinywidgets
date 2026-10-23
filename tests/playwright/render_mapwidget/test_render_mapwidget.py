from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Tolerance (px) for comparing a map's box to its container's
EPS = 2


def box(page: Page, selector: str) -> dict[str, float]:
    b = page.locator(selector).bounding_box()
    assert b is not None, selector
    return b


def card_body_content_height(page: Page, card_id: str) -> float:
    padding = page.locator(f"#{card_id} .card-body").evaluate(
        """(el) => {
          const s = getComputedStyle(el);
          return parseFloat(s.paddingTop) + parseFloat(s.paddingBottom);
        }"""
    )
    return box(page, f"#{card_id} .card-body")["height"] - padding


def test_mapwidget_backends_render_without_errors(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # maplibre is WebGL (pixels aren't readable via getImageData), so assert its
    # canvas exists and has non-zero dimensions
    canvas = page.locator("#map canvas.maplibregl-canvas")
    expect(canvas).to_have_count(1, timeout=30000)
    b = canvas.bounding_box()
    assert b is not None and b["width"] > 0 and b["height"] > 0

    # leaflet renders tiles (a 2D map, so wait for an actual tile image)
    expect(page.locator("#leaflet_map .leaflet-container")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator("#leaflet_map .leaflet-tile-loaded").first).to_be_visible(
        timeout=30000
    )

    # openlayers renders its viewport canvas
    expect(page.locator("#ol_map .ol-viewport canvas").first).to_be_visible(
        timeout=30000
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_mapwidget_fills_fixed_height_cards(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#map .maplibregl-map")).to_have_count(1, timeout=30000)
    expect(page.locator("#leaflet_map .leaflet-container")).to_have_count(
        1, timeout=30000
    )

    # Both backends' default 600px height should give way to the card's height...
    maplibre_box = box(page, "#map .maplibregl-map")
    assert (
        abs(maplibre_box["height"] - card_body_content_height(page, "fill_card")) <= EPS
    )
    assert maplibre_box["height"] > 600

    # ... whether the card is taller (above) or shorter (below) than 600px
    leaflet_box = box(page, "#leaflet_map .leaflet-container")
    assert (
        abs(leaflet_box["height"] - card_body_content_height(page, "small_card")) <= EPS
    )
    assert leaflet_box["height"] < 600

    assert_no_unexpected_errors(errors, failed_requests)


def test_mapwidget_respects_explicit_heights(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#map_output_height .leaflet-container")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator("#mapml_output_height .maplibregl-map")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator("#map_explicit_height .maplibregl-map")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator("#map_auto_height .maplibregl-map")).to_have_count(
        1, timeout=30000
    )

    # A default-height map sizes to an explicit output height (both backends)...
    assert (
        abs(box(page, "#map_output_height .leaflet-container")["height"] - 300) <= EPS
    )
    assert abs(box(page, "#mapml_output_height .maplibregl-map")["height"] - 300) <= EPS
    # ... an explicit map height wins over filling...
    assert abs(box(page, "#map_explicit_height .maplibregl-map")["height"] - 800) <= EPS
    # ... and an `auto` output height isn't definite, so the map keeps its
    # default 600px (it must not collapse to 0)
    assert abs(box(page, "#map_auto_height .maplibregl-map")["height"] - 600) <= EPS

    assert_no_unexpected_errors(errors, failed_requests)


def test_mapwidget_rerender_lifecycle(page: Page, local_app) -> None:
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


def test_mapwidget_zoom_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # The maplibre map starts at zoom 4; double-clicking zooms in, and the
    # map's zoomend handler syncs the zoom trait back to Python (browser ->
    # shinywidgets comm -> reactive_read -> UI)
    expect(page.locator("#map canvas.maplibregl-canvas")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator("#map_zoom")).to_have_text("4.0", timeout=30000)
    page.locator("#map canvas.maplibregl-canvas").dblclick()
    expect(page.locator("#map_zoom")).to_have_text("5.0", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_mapwidget_leaflet_click_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # The leaflet map's clicked_latlng trait starts empty; clicking the map
    # syncs it back to Python
    expect(page.locator("#leaflet_map .leaflet-container")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator("#leaflet_clicked")).to_have_text("[None, None]", timeout=30000)
    page.locator("#leaflet_map .leaflet-container").click()
    expect(page.locator("#leaflet_clicked")).not_to_have_text(
        "[None, None]", timeout=30000
    )

    assert_no_unexpected_errors(errors, failed_requests)
