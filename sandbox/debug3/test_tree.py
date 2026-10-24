from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import wait_for_red_pixels, expose_manager, client_models


def test_tree(page: Page, local_app) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    wait_for_red_pixels(page, "#plot canvas")
    for t in range(8):
        page.wait_for_timeout(2000)
        names = sorted(m["name"] for m in client_models(page))
        print(f"t={2*(t+1)}s:", names)
