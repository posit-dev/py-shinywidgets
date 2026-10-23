from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import wait_for_red_pixels, expose_manager, client_models


def names(page):
    return sorted(m["name"] for m in client_models(page))


def wait_tree(page, label, timeout_ms=30000):
    waited = 0
    while True:
        ns = names(page)
        if ns.count("VuetifyTemplateModel") >= 2 and ns.count("TemplateModel") >= 2:
            print(f"{label}: tree ok after {waited}ms")
            return
        if waited >= timeout_ms:
            print(f"{label}: STUCK:", ns)
            raise AssertionError(ns)
        page.wait_for_timeout(250)
        waited += 250


def test_iter(page: Page, local_app) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    wait_for_red_pixels(page, "#plot canvas")
    wait_tree(page, "load")
    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i), timeout=30000)
        expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
        wait_for_red_pixels(page, "#plot canvas")
        print(f"iter {i} after red:", names(page))
        wait_tree(page, f"iter {i}")
