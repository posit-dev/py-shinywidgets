from __future__ import annotations

from playwright.sync_api import Page, expect


def test_resize_fires_after_late_subtree_render(page: Page, local_app) -> None:
    page.goto(local_app.url)

    expect(page.locator("#ready_count")).to_have_text("1", timeout=30000)
    expect(page.locator("#resize_after_ready")).not_to_have_text("0", timeout=30000)
    expect(page.locator("#delayed_widget .delayed-render-child")).to_have_count(
        1, timeout=30000
    )
