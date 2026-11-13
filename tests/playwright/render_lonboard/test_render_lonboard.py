from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# Each lonboard map bundles its own copy of luma.gl, which logs this (harmless)
# console error when a page shows more than one map. How many of them have
# logged it by the time a test asserts depends on timing, so it can't be
# asserted on exactly.
LUMA_REINIT = "luma.gl: This version of luma.gl has already been initialized"

MEASURE_JS = """(id) => {
  const box = (el) => {
    const b = el.getBoundingClientRect();
    return {width: b.width, height: b.height, bottom: b.bottom};
  };
  const out = document.getElementById(id);
  const map = out.querySelector('.lonboard');
  return {out: box(out), map: map ? box(map) : null};
}"""


def measure(page: Page, id: str) -> dict:
    expect(page.locator(f"#{id} .lonboard canvas").first).to_be_visible(timeout=30000)
    return page.evaluate(MEASURE_JS, id)


def assert_fills(page: Page, id: str) -> None:
    m = measure(page, id)
    out, map = m["out"], m["map"]
    assert out["height"] > 200, m
    assert abs(map["width"] - out["width"]) <= 1, m
    assert abs(map["bottom"] - out["bottom"]) <= 1, m
    assert abs(map["height"] - out["height"]) <= 1, m


def test_lonboard_renders_with_controls(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    for id in ("map", "map_fixed", "map_output_height"):
        expect(page.locator(f"#{id} .lonboard canvas").first).to_be_visible(
            timeout=30000
        )
        # Map's default controls are shared module-level widgets, which only
        # display if shinywidgets gives each map its own copies
        expect(page.locator(f"#{id} .maplibregl-ctrl-fullscreen")).to_have_count(1)

    assert_no_unexpected_errors(errors, failed_requests, allowed_errors=(LUMA_REINIT,))


def test_lonboard_fills_and_respects_explicit_heights(page: Page, local_app) -> None:
    page.set_viewport_size({"width": 1200, "height": 900})
    page.goto(local_app.url)

    assert_fills(page, "map")
    tall = measure(page, "map")["map"]["height"]

    # ... and tracks its container when the window resizes
    page.set_viewport_size({"width": 1200, "height": 600})
    page.wait_for_function(
        f"() => document.querySelector('#map .lonboard').getBoundingClientRect().height < {tall - 100}"
    )
    assert_fills(page, "map")

    # Map(height=250) is respected (rather than growing to fill its card)
    fixed = measure(page, "map_fixed")
    assert abs(fixed["map"]["height"] - 250) <= 1, fixed
    assert fixed["out"]["height"] > 300, fixed

    # output_widget(height="300px") is respected
    out_height = measure(page, "map_output_height")
    assert abs(out_height["out"]["height"] - 300) <= 1, out_height
    assert abs(out_height["map"]["height"] - 300) <= 1, out_height


def test_lonboard_without_definite_height_keeps_default_height(
    page: Page, local_app
) -> None:
    page.goto(local_app.url)

    # With nothing to fill, the map keeps lonboard's own default height
    unfillable = measure(page, "map_unfillable")
    assert abs(unfillable["map"]["height"] - 500) <= 1, unfillable


def test_lonboard_view_state_roundtrips_to_python(page: Page, local_app) -> None:
    page.goto(local_app.url)

    # The browser computes the initial view state (from the data's bounds) and
    # syncs it back to Python
    view_state = page.locator("#view_state")
    expect(view_state).to_contain_text("longitude=", timeout=30000)
    before = view_state.inner_text()

    canvas = page.locator("#map .lonboard canvas").first
    expect(canvas).to_be_visible()
    # The canvas can be re-created while the map finishes initializing (e.g.,
    # when the initial view state syncs back), in which case a one-shot
    # bounding_box() call intermittently returns None. Poll the live DOM for a
    # connected, non-zero-sized canvas instead.
    box = page.wait_for_function(
        """() => {
            const c = document.querySelector('#map .lonboard canvas');
            if (!c || !c.isConnected) return false;
            const b = c.getBoundingClientRect();
            if (b.width === 0 || b.height === 0) return false;
            return {x: b.x, y: b.y, width: b.width, height: b.height};
        }"""
    ).json_value()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - 100, y, steps=10)
    page.mouse.up()

    expect(view_state).not_to_have_text(before, timeout=10000)
    expect(view_state).to_contain_text("longitude=")


def test_lonboard_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#map .lonboard canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old = page.locator("#map .lonboard").element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old)
        expect(page.locator("#map .lonboard canvas").first).to_be_visible(timeout=30000)

    expect(page.locator("#map .lonboard")).to_have_count(1)
    # One live view per displayed map (4 outputs); retired maps hold none
    map_views = [m["views"] for m in client_models(page) if m["name"] == "AnyModel"]
    assert sum(map_views) == 4, map_views

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests, allowed_errors=(LUMA_REINIT,))
