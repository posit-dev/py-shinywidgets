from __future__ import annotations

from playwright.sync_api import Page, expect


def test_shot(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    page.wait_for_timeout(5000)
    page.locator("#plot").screenshot(path="sandbox/debug3/direct.png")
