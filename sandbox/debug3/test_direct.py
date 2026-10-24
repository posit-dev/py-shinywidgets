from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import wait_for_red_pixels, expose_manager, client_models, collect_errors, assert_no_unexpected_errors


def test_direct(page: Page, local_app) -> None:
    errors, failed = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    wait_for_red_pixels(page, "#plot canvas")
    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i), timeout=30000)
        expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
        wait_for_red_pixels(page, "#plot canvas")
    page.wait_for_timeout(40000)
    print("FINAL:", sorted(m["name"] for m in client_models(page)))
    assert_no_unexpected_errors(errors, failed)
