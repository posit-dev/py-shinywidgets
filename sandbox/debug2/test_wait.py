from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import expose_manager, client_models


def test_wait_for_timeouts(page: Page, local_app) -> None:
    msgs: list[str] = []
    page.on("console", lambda msg: msgs.append(f"{msg.type}: {msg.text[:150]}"))
    page.on("pageerror", lambda err: msgs.append(f"pageerror: {err}"))
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    print("MODELS AFTER LOAD:")
    for m in client_models(page):
        print("  ", m)
    page.wait_for_timeout(45000)
    print("ERRORS AFTER 45s:", [m for m in msgs if m.startswith(("error", "pageerror"))])
