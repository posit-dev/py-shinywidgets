from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    expose_manager,
)

# kepler.gl bundles a ~12MB script and builds a WebGL map, so first paint is slow
LOAD_TIMEOUT = 60000

# Heights (px) of the output container and of the rendered kepler.gl element
# inside it, for the output with the given id
HEIGHTS_JS = """(id) => {
  const out = document.getElementById(id);
  const kepler = out && out.querySelector('.kepler-gl');
  if (!kepler) return null;
  return { container: out.clientHeight, kepler: kepler.getBoundingClientRect().height };
}"""

# True once the kepler.gl element's height matches its container's (within a pixel)
KEPLER_MATCHES_CONTAINER_JS = """(id) => {
  const out = document.getElementById(id);
  const kepler = out && out.querySelector('.kepler-gl');
  if (!kepler) return false;
  const h = kepler.getBoundingClientRect().height;
  return Math.abs(h - out.clientHeight) <= 1;
}"""

LIVE_VIEWS_JS = "() => window.widgetManager._liveViews.size"


def test_keplergl_renders_map(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    canvas = page.locator("#map .kepler-gl canvas").first
    expect(canvas).to_be_visible(timeout=LOAD_TIMEOUT)
    box = canvas.bounding_box()
    assert box is not None and box["width"] > 0 and box["height"] > 0

    assert_no_unexpected_errors(errors, failed_requests)


def test_keplergl_fills_container_and_respects_explicit_height(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#map .kepler-gl")).to_be_visible(timeout=LOAD_TIMEOUT)
    expect(page.locator("#fixed_map .kepler-gl")).to_be_visible(timeout=LOAD_TIMEOUT)

    # Fill: the map takes the full height of its (card-padded) container,
    # rather than kepler.gl's default 400px
    page.wait_for_function(KEPLER_MATCHES_CONTAINER_JS, arg="map", timeout=10000)
    fill = page.evaluate(HEIGHTS_JS, "map")
    assert fill["container"] > 400
    assert abs(fill["kepler"] - fill["container"]) <= 1

    # The Python-side widget learns the size the browser settled on
    expect(page.locator("#map_height")).to_have_text(
        f"height: {round(fill['kepler'])}", timeout=10000
    )

    # Explicit height on output_widget(): the map is that tall, not 400px
    page.wait_for_function(KEPLER_MATCHES_CONTAINER_JS, arg="fixed_map", timeout=10000)
    fixed = page.evaluate(HEIGHTS_JS, "fixed_map")
    assert fixed["container"] == 300
    assert abs(fixed["kepler"] - 300) <= 1

    # A height set on the KeplerGl widget itself is left alone
    expect(page.locator("#tall_map .kepler-gl")).to_be_visible(timeout=LOAD_TIMEOUT)
    tall = page.evaluate(HEIGHTS_JS, "tall_map")
    assert abs(tall["kepler"] - 250) <= 1

    # The fill tracks its container as that changes
    page.evaluate("document.getElementById('fill_card').style.height = '350px'")
    page.wait_for_function(
        "() => Math.abs(document.querySelector('#map .kepler-gl')"
        ".getBoundingClientRect().height - document.getElementById('map').clientHeight) <= 1"
        " && document.getElementById('map').clientHeight < 350",
        timeout=10000,
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_keplergl_config_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # Once kepler has loaded the data, it syncs the layers it created into its
    # `config` trait (browser -> reactive_read)
    expect(page.locator("#n_layers")).to_have_text(
        re.compile(r"layers: [1-9]"), timeout=LOAD_TIMEOUT
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_keplergl_renders_dataframe_with_missing_values(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # A NaN in the returned DataFrame must not end the session, and kepler
    # still creates layers for the data
    expect(page.locator("#missing_values_layers")).to_have_text(
        re.compile(r"layers: [1-9]"), timeout=LOAD_TIMEOUT
    )
    page.click("#rerender")
    expect(page.locator("#render_count")).to_have_text("1")

    assert_no_unexpected_errors(errors, failed_requests)


def test_keplergl_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#map .kepler-gl")).to_have_count(1, timeout=LOAD_TIMEOUT)
    expect(page.locator("#render_count")).to_have_text("0")
    page.wait_for_function(KEPLER_MATCHES_CONTAINER_JS, arg="map", timeout=10000)
    initial_views = page.evaluate(LIVE_VIEWS_JS)

    for i in range(1, 4):
        old = page.locator("#map .kepler-gl").element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old, timeout=LOAD_TIMEOUT)
        expect(page.locator("#map .kepler-gl")).to_have_count(1, timeout=LOAD_TIMEOUT)
        page.wait_for_function(KEPLER_MATCHES_CONTAINER_JS, arg="map", timeout=10000)

    # Re-rendering replaces the widget, but old views must be disposed (no
    # accumulation of maps)
    assert page.evaluate(LIVE_VIEWS_JS) == initial_views

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
