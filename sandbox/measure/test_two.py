from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import collect_errors


def test_one(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#fill_plot canvas").first).to_be_visible(timeout=30000)


def test_two(page: Page, local_app) -> None:
    errors, failed = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#fill_plot canvas").first).to_be_visible(timeout=30000)
    page.wait_for_timeout(3000)
    print("ERRORS:", errors)
    print("FAILED:", failed)
