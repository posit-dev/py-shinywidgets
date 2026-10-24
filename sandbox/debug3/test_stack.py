from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import wait_for_red_pixels


def test_stack(page: Page, local_app) -> None:
    errs: list[str] = []
    page.on("console", lambda msg: errs.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: errs.append(f"PAGEERROR: {err}"))
    page.goto(local_app.url)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    wait_for_red_pixels(page, "#plot canvas")
    page.click("#rerender")
    expect(page.locator("#render_count")).to_have_text("1", timeout=30000)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    wait_for_red_pixels(page, "#plot canvas")
    page.wait_for_timeout(40000)
    for e in errs:
        if "Timeout" in e:
            print("FULL ERROR:")
            print(e)
            print("=====")
            break
