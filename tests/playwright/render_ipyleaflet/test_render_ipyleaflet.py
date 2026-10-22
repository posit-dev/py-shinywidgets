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

    expect(page.locator("#lmap .leaflet-container")).to_have_count(1, timeout=30000)
    expect(page.locator("#lmap .leaflet-marker-icon")).to_have_count(1)
    expect(page.locator("#lmap .leaflet-tile-loaded").first).to_be_visible(
        timeout=30000
    )

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
    assert abs(leaflet["height"] - (body["height"] - padding["y"])) <= EPS
    assert abs(leaflet["width"] - (body["width"] - padding["x"])) <= EPS


def test_render_ipyleaflet_fills_fixed_height_card(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#lmap .leaflet-container")).to_have_count(1, timeout=30000)
    expect(page.locator("#map_small_card .leaflet-container")).to_have_count(
        1, timeout=30000
    )

    # Taller than leaflet's built-in 400px height...
    assert_fills_card_body(page, "fill_card", "lmap")
    assert box(page, "#lmap .leaflet-container")["height"] > 400
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
    assert abs(output_height - 300) <= EPS
    assert abs(tall_height - 600) <= EPS
    assert abs(layout_height - 250) <= EPS

    assert_no_unexpected_errors(errors, failed_requests)


def test_render_ipyleaflet_keeps_default_height_for_intrinsic_output_height(
    page: Page, local_app
) -> None:
    # `height: auto` is not a definite height, so the map must not take 100% of it
    # (that would collapse it to 0px); it keeps ipyleaflet's default instead
    page.goto(local_app.url)
    expect(page.locator("#map_auto_height .leaflet-container")).to_have_count(
        1, timeout=30000
    )
    assert abs(box(page, "#map_auto_height .leaflet-container")["height"] - 400) <= EPS


def test_render_ipyleaflet_layout_height_wins_over_output_height(
    page: Page, local_app
) -> None:
    page.goto(local_app.url)
    sel = "#map_layout_in_output_height .leaflet-container"
    expect(page.locator(sel)).to_have_count(1, timeout=30000)
    assert abs(box(page, sel)["height"] - 250) <= EPS


def test_render_ipyleaflet_controls_follow_theme(page: Page, local_app) -> None:
    # jupyter-leaflet colors controls with JupyterLab theme variables, which don't
    # exist in Shiny (the zoom buttons would be transparent)
    page.goto(local_app.url)
    zoom_in = page.locator("#lmap .leaflet-control-zoom-in")
    expect(zoom_in).to_be_visible(timeout=30000)
    bg_js = "el => getComputedStyle(el).backgroundColor"
    body_bg_js = "getComputedStyle(document.body).backgroundColor"

    light = zoom_in.evaluate(bg_js)
    assert light == page.evaluate(body_bg_js) != "rgba(0, 0, 0, 0)"

    page.evaluate("document.documentElement.setAttribute('data-bs-theme', 'dark')")
    dark = zoom_in.evaluate(bg_js)
    assert dark == page.evaluate(body_bg_js) != light


def test_render_ipyleaflet_zoom_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#zoom_text")).to_have_text("4.0", timeout=30000)
    page.locator("#lmap .leaflet-control-zoom-in").click()
    expect(page.locator("#zoom_text")).to_have_text("5.0", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_render_ipyleaflet_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#lmap .leaflet-container")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    def live_map_views() -> int:
        # Maps whose model is retired on rerender are closed, so only the live
        # ones (7 outputs) should still hold a view
        return sum(
            m["views"] for m in client_models(page) if m["name"] == "LeafletMapModel"
        )

    initial = live_map_views()
    assert initial == 7

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator("#lmap .leaflet-marker-icon")).to_have_count(1)

    expect(page.locator("#lmap .leaflet-container")).to_have_count(1)
    assert live_map_views() == initial

    assert_no_unexpected_errors(errors, failed_requests)
