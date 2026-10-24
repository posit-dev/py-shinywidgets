from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
)

# Tolerance (px) for comparing a map's box to its container's
EPS = 2

local_app_plotly = create_app_fixture(Path(__file__).parent / "app_plotly.py")


def box(page: Page, selector: str) -> dict[str, float]:
    b = page.locator(selector).bounding_box()
    assert b is not None, selector
    return b


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


def test_render_leafmap_renders_map_without_errors(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#default_map .leaflet-container")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator("#default_map .leaflet-marker-icon")).to_have_count(1)
    expect(page.locator("#default_map .leaflet-tile-loaded").first).to_be_visible(
        timeout=30000
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_render_leafmap_treats_leafmaps_default_height_as_unset(
    page: Page, local_app
) -> None:
    page.goto(local_app.url)
    expect(page.locator("#default_map .leaflet-container")).to_have_count(
        1, timeout=30000
    )

    # leafmap's 600px default would overflow a 450px card; the map should fill it
    assert_fills_card_body(page, "fill_card", "default_map")
    assert box(page, "#default_map .leaflet-container")["height"] < 600

    # Nothing is clipped: the map's bottom controls sit inside the map
    leaflet = box(page, "#default_map .leaflet-container")
    attribution = box(page, "#default_map .leaflet-control-attribution")
    assert (
        attribution["y"] + attribution["height"]
        <= leaflet["y"] + leaflet["height"] + EPS
    )


def test_render_leafmap_fills_card(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#card_map .leaflet-container")).to_have_count(1, timeout=30000)

    assert_fills_card_body(page, "small_card", "card_map")


def test_render_leafmap_respects_an_explicit_height(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#explicit_height_map .leaflet-container")).to_have_count(
        1, timeout=30000
    )

    leaflet = box(page, "#explicit_height_map .leaflet-container")
    assert abs(leaflet["height"] - 250) <= EPS


def test_render_leafmap_bounds_are_reactive(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#default_map .leaflet-container")).to_have_count(
        1, timeout=30000
    )

    # bounds_text reports the map's south-west corner as "lat,lon"
    bounds_text = page.locator("#bounds_text")
    expect(bounds_text).to_have_text(re.compile(r"^-?\d+,-?\d+$"), timeout=30000)
    before = bounds_text.inner_text()

    # Zooming in directly on the map should narrow the bounds
    page.locator("#default_map .leaflet-control-zoom-in").click()
    expect(bounds_text).not_to_have_text(before, timeout=30000)


def test_render_leafmap_plotly_fills_and_updates_in_place(
    page: Page, local_app_plotly: ShinyAppProc
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_plotly.url)
    expect(page.locator("#plot .scatterlayer .point")).to_have_count(2, timeout=30000)

    page.evaluate(
        "window.leafmapPlotlyGraph = document.querySelector('#plot .js-plotly-plot')"
    )
    page.wait_for_function(
        """() => {
          const body = document.querySelector('#plotly_card .card-body');
          const style = getComputedStyle(body);
          const height = body.clientHeight
            - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
          return Math.abs(window.leafmapPlotlyGraph._fullLayout.height - height) <= 2;
        }"""
    )
    assert box(page, "#plot .js-plotly-plot")["height"] < 600

    page.click("#update")
    page.wait_for_function(
        "() => window.leafmapPlotlyGraph.data[0].marker.color === 'blue'"
    )
    assert page.evaluate(
        "window.leafmapPlotlyGraph === document.querySelector('#plot .js-plotly-plot')"
    )
    assert_no_unexpected_errors(errors, failed_requests)
