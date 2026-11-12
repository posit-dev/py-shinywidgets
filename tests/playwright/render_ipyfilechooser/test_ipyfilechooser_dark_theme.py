from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

pytest.importorskip("ipyfilechooser")

local_app_dark = create_app_fixture(Path(__file__).parent / "app_dark.py")

# ipyfilechooser hard-codes its "No selection" label to black in an inline
# style; in dark mode shinywidgets.css overrides it to the body color, scoped
# to the class ipyfilechooser_layout_defaults() adds to the chooser
LABEL_COLOR_JS = """() => {
  const label = document.querySelector('#chooser span[style*="color:black"]');
  return [getComputedStyle(label).color, getComputedStyle(document.body).color];
}"""


def test_dark_app_no_selection_label_follows_dark_mode(
    page: Page, local_app_dark
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_dark.url)

    label = page.locator('#chooser span[style*="color:black"]')
    expect(label).to_have_text("No selection", timeout=30000)

    # Without the scoped override the label stays black on the dark page
    label_color, body_color = page.evaluate(LABEL_COLOR_JS)
    assert label_color == body_color

    assert_no_unexpected_errors(errors, failed_requests)
