from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# Tolerance (px) for comparing a map's box to its container's
EPS = 2


def box(page: Page, selector: str) -> dict[str, float]:
    b = page.locator(selector).bounding_box()
    assert b is not None, selector
    return b


def test_render_ipyleaflet_renders_tiles_without_errors(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#map .leaflet-container")).to_have_count(1, timeout=30000)
    expect(page.locator("#map .leaflet-marker-icon")).to_have_count(1)
    expect(page.locator("#map .leaflet-tile-loaded").first).to_be_visible(timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def assert_fills_card_body(page: Page, card_id: str, map_id: str) -> None:
    # The map should fill the card body's content box (i.e., minus its padding)
    padding = page.locator(f"#{card_id} .card-body").evaluate(
        """(el) => {
          const s = getComputedStyle(el);
          return {
            x: parseFloat(s.paddingLeft) + parseFloat(s.paddingRight),
            y: parseFloat(s.paddingTop) + parseFloat(s.paddingBottom),
          };
        }"""
    )
    body = box(page, f"#{card_id} .card-body")
    leaflet = box(page, f"#{map_id} .leaflet-container")
    print(f"{card_id}: card-body={body} padding={padding} leaflet={leaflet}")
    assert abs(leaflet["height"] - (body["height"] - padding["y"])) <= EPS
    assert abs(leaflet["width"] - (body["width"] - padding["x"])) <= EPS


def test_render_ipyleaflet_fills_fixed_height_card(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#map .leaflet-container")).to_have_count(1, timeout=30000)
    expect(page.locator("#map_small_card .leaflet-container")).to_have_count(
        1, timeout=30000
    )

    # Taller than leaflet's built-in 400px height...
    assert_fills_card_body(page, "fill_card", "map")
    assert box(page, "#map .leaflet-container")["height"] > 400
    # ... and shorter than it
    assert_fills_card_body(page, "small_card", "map_small_card")
    assert box(page, "#map_small_card .leaflet-container")["height"] < 400

    assert_no_unexpected_errors(errors, failed_requests)


def test_render_ipyleaflet_respects_explicit_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#map_output_height .leaflet-container")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator("#map_layout_height .leaflet-container")).to_have_count(
        1, timeout=30000
    )

    expect(page.locator("#map_tall .leaflet-container")).to_have_count(1, timeout=30000)

    output_height = box(page, "#map_output_height .leaflet-container")["height"]
    tall_height = box(page, "#map_tall .leaflet-container")["height"]
    layout_height = box(page, "#map_layout_height .leaflet-container")["height"]
    print(
        f"output_widget(height=300px)={output_height} Layout(height=250px)={layout_height}"
    )
    assert abs(output_height - 300) <= EPS
    assert abs(tall_height - 600) <= EPS
    assert abs(layout_height - 250) <= EPS

    assert_no_unexpected_errors(errors, failed_requests)


def test_render_ipyleaflet_zoom_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#zoom_text")).to_have_text("4.0", timeout=30000)
    page.locator("#map .leaflet-control-zoom-in").click()
    expect(page.locator("#zoom_text")).to_have_text("5.0", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_render_ipyleaflet_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#map .leaflet-container")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    def live_map_views() -> int:
        # Maps whose model is retired on rerender are closed, so only the live
        # ones (5 outputs) should still hold a view
        return sum(
            m["views"] for m in client_models(page) if m["name"] == "LeafletMapModel"
        )

    initial = live_map_views()
    assert initial == 5

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator("#map .leaflet-marker-icon")).to_have_count(1)

    expect(page.locator("#map .leaflet-container")).to_have_count(1)
    assert live_map_views() == initial

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
