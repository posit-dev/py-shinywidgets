from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_app_defined_ipyreact_subclass_renders_and_syncs(page: Page, local_app) -> None:
    # This doesn't depend on how the subclass's own JavaScript is looked up:
    # ipyreact's import-time registry widgets already register its bundle in
    # every session (tests/unit/test_dependencies.py covers the lookup).
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    button = page.locator("#counter button")
    expect(button).to_have_text("Clicked 0 times", timeout=30000)

    button.click()
    expect(button).to_have_text("Clicked 1 times")
    expect(page.locator("#value")).to_have_text("1")

    assert_no_unexpected_errors(errors, failed_requests)
