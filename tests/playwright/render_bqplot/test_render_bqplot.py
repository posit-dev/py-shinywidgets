from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    expose_manager,
    settled_live_views,
)

# Resolves --bs-body-bg to an rgb() string (a custom property's raw value could be
# a hex color, so let the browser compute it) alongside the plot area's fill
THEME_COLORS_JS = """(sel) => {
  const rect = document.querySelector(sel + ' .plotarea_background');
  const probe = document.createElement('div');
  probe.style.backgroundColor = 'var(--bs-body-bg)';
  document.body.appendChild(probe);
  const bodyBg = getComputedStyle(probe).backgroundColor;
  probe.remove();
  return { fill: getComputedStyle(rect).fill, bodyBg };
}"""

# Height of the output element, the figure inside it, and the content box
# (excluding padding) of the card body holding it
FILL_BOXES_JS = """() => {
  const out = document.querySelector('#fig');
  const fig = out.querySelector('.bqplot');
  const body = out.closest('.card-body');
  const cs = getComputedStyle(body);
  const pad = (p) => parseFloat(cs.getPropertyValue(p));
  return {
    out: out.getBoundingClientRect().height,
    fig: fig.getBoundingClientRect().height,
    figWidth: fig.getBoundingClientRect().width,
    outWidth: out.getBoundingClientRect().width,
    bodyHeight: body.clientHeight - pad('padding-top') - pad('padding-bottom'),
    bodyWidth: body.clientWidth - pad('padding-left') - pad('padding-right'),
  };
}"""

HEIGHT_JS = """(sel) => {
  const out = document.querySelector(sel);
  return {
    out: out.getBoundingClientRect().height,
    fig: out.querySelector('.bqplot').getBoundingClientRect().height,
  };
}"""

local_app_tooltip = create_app_fixture(Path(__file__).parent / "app_tooltip.py")


def test_bqplot_renders_with_theme_colors(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#fig .bqplot svg").first).to_be_visible(timeout=30000)
    expect(page.locator("#fig .dot")).to_have_count(4)
    expect(page.locator("#fig_height .bqplot svg").first).to_be_visible()

    # bqplot's stylesheet reads JupyterLab theme variables; without them the plot
    # area fill is invalid and falls back to black. It should follow Shiny's theme.
    light = page.evaluate(THEME_COLORS_JS, "#fig")
    assert light["fill"] == light["bodyBg"] != "rgb(0, 0, 0)"

    page.evaluate("document.documentElement.setAttribute('data-bs-theme', 'dark')")
    dark = page.evaluate(THEME_COLORS_JS, "#fig")
    assert dark["fill"] == dark["bodyBg"]
    assert dark["fill"] != light["fill"]

    assert_no_unexpected_errors(errors, failed_requests)


def test_bqplot_fills_fixed_height_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#fig .dot")).to_have_count(4, timeout=30000)

    boxes = page.evaluate(FILL_BOXES_JS)
    assert abs(boxes["fig"] - boxes["bodyHeight"]) <= 1
    assert abs(boxes["out"] - boxes["bodyHeight"]) <= 1
    assert abs(boxes["figWidth"] - boxes["bodyWidth"]) <= 1

    # ... and it tracks the container's width when the window resizes
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(
        """() => {
          const fig = document.querySelector('#fig .bqplot').getBoundingClientRect();
          return fig.width < 600;
        }"""
    )
    boxes = page.evaluate(FILL_BOXES_JS)
    assert abs(boxes["fig"] - boxes["bodyHeight"]) <= 1
    assert abs(boxes["figWidth"] - boxes["bodyWidth"]) <= 1

    assert_no_unexpected_errors(errors, failed_requests)


def test_bqplot_respects_explicit_heights(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#fig_height .bqplot svg").first).to_be_visible(timeout=30000)
    expect(page.locator("#fig_layout .bqplot svg").first).to_be_visible()

    on_output = page.evaluate(HEIGHT_JS, "#fig_height")
    assert on_output["out"] == 250
    assert on_output["fig"] == 250

    on_layout = page.evaluate(HEIGHT_JS, "#fig_layout")
    assert on_layout["fig"] == 300

    # An intrinsic output height isn't definite, so the figure keeps bqplot's own
    # (480px) height rather than taking 100% of it
    expect(page.locator("#fig_auto .bqplot svg").first).to_be_visible()
    on_auto = page.evaluate(HEIGHT_JS, "#fig_auto")
    assert on_auto["fig"] == 480

    assert_no_unexpected_errors(errors, failed_requests)


def test_bqplot_selection_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#selected")).to_have_text("None", timeout=30000)
    expect(page.locator("#fig .dot")).to_have_count(4)

    # Clicking a point sets Scatter.selected (browser -> comm -> reactive_read)
    page.locator("#fig .dot").nth(2).click()
    expect(page.locator("#selected")).to_have_text("[2]", timeout=30000)

    page.locator("#fig .dot").nth(0).click()
    expect(page.locator("#selected")).to_have_text("[0]", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_bqplot_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#fig .dot")).to_have_count(4, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")
    initial = settled_live_views(page)

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator("#fig .dot")).to_have_count(4)

    # Re-rendering replaces the figure; the old views must be disposed
    expect(page.locator("#fig .bqplot")).to_have_count(1)
    assert settled_live_views(page) == initial

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)


def test_bqplot_tooltip_follows_theme(page: Page, local_app_tooltip) -> None:
    # bqplot appends tooltips to <body>, outside the figure, so the theme variables
    # must reach them there too (otherwise the tooltip has no background or border)
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_tooltip.url)
    expect(page.locator("#fig .dot")).to_have_count(3, timeout=30000)

    page.locator("#fig .dot").nth(1).hover()
    tooltip = page.locator("body > .bqplot_tooltip_div .bqplot_mark_tooltip").first
    expect(tooltip).to_be_visible()
    style_js = (
        "el => { const s = getComputedStyle(el); "
        "return { bg: s.backgroundColor, border: s.borderTopStyle }; }"
    )
    body_bg_js = "getComputedStyle(document.body).backgroundColor"
    light = tooltip.evaluate(style_js)
    assert light == {"bg": page.evaluate(body_bg_js), "border": "solid"}, light

    page.evaluate("document.documentElement.setAttribute('data-bs-theme', 'dark')")
    dark = tooltip.evaluate(style_js)
    assert dark == {"bg": page.evaluate(body_bg_js), "border": "solid"}, dark
    assert dark["bg"] != light["bg"]

    assert_no_unexpected_errors(errors, failed_requests)
