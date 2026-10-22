from __future__ import annotations

from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc

sizing_app = create_app_fixture("app_sizing.py")
express_app = create_app_fixture("app_express.py")

MEASURE_JS = """(id) => {
  const box = (el) => {
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return {width: b.width, height: b.height, bottom: b.bottom};
  };
  const out = document.getElementById(id);
  return {
    out: box(out),
    map: box(out.querySelector('.maplibregl-map')),
    canvas: box(out.querySelector('canvas.maplibregl-canvas')),
    attrib: box(out.querySelector('.maplibregl-ctrl-attrib')),
  };
}"""

# The map (and its canvas, which maplibre resizes asynchronously) is `height`
# tall and sits entirely within the output, so its bottom controls aren't
# clipped
MAP_HAS_HEIGHT_JS = f"""([id, height]) => {{
  const m = ({MEASURE_JS})(id);
  if (!m.map || !m.canvas || !m.attrib) return false;
  const near = (a, b) => Math.abs(a - b) <= 1;
  return near(m.map.height, height) && near(m.canvas.height, height) &&
    m.attrib.bottom <= m.out.bottom + 1;
}}"""


def measure(page: Page, id: str) -> dict:
    return page.evaluate(MEASURE_JS, id)


def expect_map_height(page: Page, id: str, height: float) -> dict:
    expect(page.locator(f"#{id} canvas.maplibregl-canvas")).to_be_visible(timeout=30000)
    try:
        page.wait_for_function(MAP_HAS_HEIGHT_JS, arg=[id, height], timeout=10000)
    except PlaywrightTimeoutError:
        raise AssertionError(f"#{id} map isn't {height}px tall: {measure(page, id)}")
    return measure(page, id)


def expect_map_fills(page: Page, id: str) -> dict:
    expect(page.locator(f"#{id} canvas.maplibregl-canvas")).to_be_visible(timeout=30000)
    out = measure(page, id)["out"]
    assert out["height"] > 300, measure(page, id)
    m = expect_map_height(page, id, out["height"])
    assert abs(m["map"]["width"] - m["out"]["width"]) <= 1, m
    assert abs(m["map"]["bottom"] - m["out"]["bottom"]) <= 1, m
    return m


def test_maplibre_fills_card(page: Page, sizing_app: ShinyAppProc) -> None:
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(sizing_app.url)

    normal = expect_map_fills(page, "fill")

    # ... and follows the card into (and back out of) full screen
    page.locator("#fill").hover()
    page.locator(".bslib-full-screen-enter").first.click()
    full = expect_map_fills(page, "fill")
    assert full["out"]["height"] > normal["out"]["height"] + 100, (normal, full)

    page.keyboard.press("Escape")
    expect_map_height(page, "fill", normal["out"]["height"])


def test_maplibre_fills_hidden_tab_once_shown(
    page: Page, sizing_app: ShinyAppProc
) -> None:
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(sizing_app.url)

    page.get_by_role("tab", name="Map").click()
    expect_map_fills(page, "hidden_tab")


def test_maplibre_respects_explicit_heights(
    page: Page, sizing_app: ShinyAppProc
) -> None:
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(sizing_app.url)

    # output_widget(height=) sizes the map to the output (rather than cropping
    # or under-filling it)
    for id, height in (("output_250", 250), ("output_600", 600)):
        m = expect_map_height(page, id, height)
        assert abs(m["out"]["height"] - height) <= 1, m

    # MapWidget(height=) is respected, even inside a filling card
    m = expect_map_height(page, "widget_height", 200)
    assert m["out"]["height"] > 300, m

    # With nothing to fill, the map keeps MapWidget's height (400px by default)
    expect_map_height(page, "unfillable_default", 400)
    expect_map_height(page, "unfillable_600", 600)


def test_maplibre_express_renderer_height(
    page: Page, express_app: ShinyAppProc
) -> None:
    page.goto(express_app.url)

    m = expect_map_height(page, "map", 250)
    assert abs(m["out"]["height"] - 250) <= 1, m
