from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import count_red_pixels


def test_count(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    page.wait_for_timeout(4000)
    print("RED PIXELS:", count_red_pixels(page, "#plot canvas"))
