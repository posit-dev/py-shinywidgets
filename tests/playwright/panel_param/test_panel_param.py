from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_panel_param_follows_browser_and_python_changes(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    # Seeded with the slider's value at render
    expect(page.locator("#value")).to_have_text("5", timeout=30000)

    # Browser interaction: keyboard-step the slider handle (bokeh sliders are
    # noUiSlider-based, so the focused handle steps on arrow keys)
    handle = page.locator("#slider .noUi-handle")
    handle.click()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    expect(page.locator("#value")).to_have_text("7", timeout=5000)

    # A Python-side change to the same parameter invalidates readers too
    page.click("#bump")
    expect(page.locator("#value")).to_have_text("9", timeout=5000)
    # ... and syncs back to the browser slider
    expect(handle).to_have_attribute("aria-valuenow", "9.0", timeout=5000)

    assert_no_unexpected_errors(errors, failed_requests)
