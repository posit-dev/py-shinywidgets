from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

pytest.importorskip("reactable")

local_app_dark = create_app_fixture(Path(__file__).parent / "app_dark.py")
local_app_light = create_app_fixture(Path(__file__).parent / "app_light.py")
local_app_dark_themed = create_app_fixture(Path(__file__).parent / "app_dark_themed.py")

TABLE_BG_JS = """() => {
  const el = document.querySelector('#tbl .Reactable');
  return getComputedStyle(el).backgroundColor;
}"""

# The table text is (and should stay) inherited from the page, so compare
# against the body's computed color rather than hardcoding Bootstrap's
CELL_COLOR_JS = """() => {
  const cell = document.querySelector('#tbl .rt-tbody .rt-td');
  return [getComputedStyle(cell).color, getComputedStyle(document.body).color];
}"""


def wait_for_table(page: Page) -> None:
    expect(page.locator("#tbl .ReactTable")).to_have_count(1, timeout=30000)
    expect(page.locator("#tbl .rt-tbody .rt-td").first).to_be_visible(timeout=30000)


def test_dark_app_table_follows_dark_mode(page: Page, local_app_dark) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_dark.url)
    wait_for_table(page)

    # Without the fix, .Reactable keeps its stylesheet's fixed #fff background
    # while the text inherits the page's light dark-mode body color (#460)
    assert page.evaluate(TABLE_BG_JS) == "rgba(0, 0, 0, 0)"
    cell_color, body_color = page.evaluate(CELL_COLOR_JS)
    assert cell_color == body_color

    assert_no_unexpected_errors(errors, failed_requests)


def test_light_app_table_unchanged(page: Page, local_app_light) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_light.url)
    wait_for_table(page)

    assert page.evaluate(TABLE_BG_JS) == "rgb(255, 255, 255)"
    cell_color, body_color = page.evaluate(CELL_COLOR_JS)
    assert cell_color == body_color

    assert_no_unexpected_errors(errors, failed_requests)


def test_dark_app_user_theme_wins(page: Page, local_app_dark_themed) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_dark_themed.url)
    wait_for_table(page)

    # A user-supplied theme= applies through a generated `reactable-<hash>`
    # class, which the dark-mode rules in shinywidgets.css are careful not to
    # override (a themed table keeps its own colors in dark mode)
    assert page.evaluate(TABLE_BG_JS) == "rgb(34, 68, 102)"
    cell_color, _ = page.evaluate(CELL_COLOR_JS)
    assert cell_color == "rgb(255, 0, 255)"

    assert_no_unexpected_errors(errors, failed_requests)


def test_table_follows_mode_toggle(page: Page, local_app_dark) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_dark.url)
    wait_for_table(page)

    # The fix is pure CSS keyed on data-bs-theme, so toggling the mode
    # re-themes the table with no re-render (write the same attribute
    # bslib's dark-mode input writes)
    page.evaluate("() => document.documentElement.dataset.bsTheme = 'light'")
    assert page.evaluate(TABLE_BG_JS) == "rgb(255, 255, 255)"
    cell_color, body_color = page.evaluate(CELL_COLOR_JS)
    assert cell_color == body_color

    page.evaluate("() => document.documentElement.dataset.bsTheme = 'dark'")
    assert page.evaluate(TABLE_BG_JS) == "rgba(0, 0, 0, 0)"
    cell_color, body_color = page.evaluate(CELL_COLOR_JS)
    assert cell_color == body_color

    assert_no_unexpected_errors(errors, failed_requests)
