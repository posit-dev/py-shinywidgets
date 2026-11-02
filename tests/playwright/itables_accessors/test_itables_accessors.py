from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_selection_rows_follows_clicks_and_sort(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    rows = page.locator("#table tbody tr")
    expect(rows.first).to_be_visible(timeout=30000)
    expect(page.locator("#sel")).to_have_text("[]", timeout=30000)

    # Click the second row: position 1 in data order
    rows.nth(1).click()
    expect(page.locator("#sel")).to_have_text("[1]", timeout=30000)

    # Sort the `n` column descending (two clicks on its sort icon), then click
    # the first row: it's n=49, and positions are in data order, not display
    # order
    sort_icon = page.locator("#table thead th").first.locator(".dt-column-order")
    sort_icon.click()
    sort_icon.click()
    rows.nth(0).click()
    expect(page.locator("#sel")).to_have_text("[49]", timeout=30000)

    # Searching never syncs the selection
    page.locator("#table input[type=search]").fill("item 4")
    expect(page.locator("#sel")).to_have_text("[49]", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)
