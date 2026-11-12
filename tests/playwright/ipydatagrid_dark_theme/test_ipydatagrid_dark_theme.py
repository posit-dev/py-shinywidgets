from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

local_app_light = create_app_fixture(Path(__file__).parent / "app_light.py")
local_app_plain = create_app_fixture(Path(__file__).parent / "app_plain.py")

# ipydatagrid picks its light/dark palette once, when the grid view is
# created, by reading JupyterLab's `data-jp-theme-light` attribute on <body>
# (dark iff the attribute is "false"), which JupyterLab sets but Shiny
# doesn't. shinywidgets emulates it from the app's bslib color mode
# (`data-bs-theme` on <html>), kept in sync as the mode changes.
JP_THEME_LIGHT_JS = "() => document.body.dataset.jpThemeLight"

# The grid is canvas-drawn, so sample a column-header pixel to see which
# palette was drawn: the header fill is --ipydatagrid-layout-color2
# (#eeeeee in the light palette, #424242 in the dark palette)
HEADER_PIXEL_JS = """() => {
  const c = document.querySelector('#grid .lm-DataGrid canvas');
  if (!c || !c.width || !c.height) return null;
  const d = c.getContext('2d').getImageData(Math.floor(c.width / 2), 5, 1, 1).data;
  return [d[0], d[1], d[2], d[3]];
}"""


def wait_for_grid(page: Page) -> None:
    expect(page.locator("#grid .lm-DataGrid")).to_have_count(1, timeout=30000)
    expect(page.locator("#grid .ipydatagrid-widget canvas").first).to_be_visible()


def header_is_dark(page: Page) -> bool:
    pixel = page.evaluate(HEADER_PIXEL_JS)
    assert pixel is not None
    assert pixel[3] == 255
    return pixel[0] < 128 and pixel[1] < 128 and pixel[2] < 128


def test_dark_app_grid_uses_dark_palette(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_grid(page)

    page.wait_for_function(f"() => ({JP_THEME_LIGHT_JS})() === 'false'")

    # ipydatagrid froze the dark palette at view creation: it marks the widget
    # `dark` and draws the dark header color
    expect(page.locator("#grid .ipydatagrid-widget.dark")).to_have_count(1)
    assert header_is_dark(page)

    assert_no_unexpected_errors(errors, failed_requests)


def test_light_app_grid_uses_light_palette(page: Page, local_app_light) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_light.url)
    wait_for_grid(page)

    page.wait_for_function(f"() => ({JP_THEME_LIGHT_JS})() === 'true'")

    expect(page.locator("#grid .ipydatagrid-widget.dark")).to_have_count(0)
    assert not header_is_dark(page)

    assert_no_unexpected_errors(errors, failed_requests)


def test_plain_app_ignores_os_dark_preference(page: Page, local_app_plain) -> None:
    errors, failed_requests = collect_errors(page)
    page.emulate_media(color_scheme="dark")
    page.goto(local_app_plain.url)
    wait_for_grid(page)

    # A page without input_dark_mode() has no data-bs-theme attribute and is
    # always light (Bootstrap's default), so the OS preference must not leak
    # into the grid's palette
    page.wait_for_function(f"() => ({JP_THEME_LIGHT_JS})() === 'true'")
    expect(page.locator("#grid .ipydatagrid-widget.dark")).to_have_count(0)
    assert not header_is_dark(page)

    assert_no_unexpected_errors(errors, failed_requests)


def test_attribute_follows_theme_toggle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_grid(page)
    page.wait_for_function(f"() => ({JP_THEME_LIGHT_JS})() === 'false'")

    # Toggling the app's color mode (here via the same attribute bslib's dark
    # mode input writes) updates the JupyterLab attribute, so widgets whose JS
    # loads later still see the current mode. (Already-rendered grids keep the
    # palette they froze at view creation -- an upstream ipydatagrid
    # limitation.)
    page.evaluate(
        "() => document.documentElement.setAttribute('data-bs-theme', 'light')"
    )
    page.wait_for_function(f"() => ({JP_THEME_LIGHT_JS})() === 'true'")

    page.evaluate(
        "() => document.documentElement.setAttribute('data-bs-theme', 'dark')"
    )
    page.wait_for_function(f"() => ({JP_THEME_LIGHT_JS})() === 'false'")

    assert_no_unexpected_errors(errors, failed_requests)
