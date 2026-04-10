from __future__ import annotations

import time

from playwright.sync_api import Page
from shiny.run import ShinyAppProc


def assert_rerender_cleanup(page: Page, local_app: ShinyAppProc, ready_selector: str) -> None:
    errors: list[str] = []

    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    page.wait_for_selector(ready_selector, timeout=30000)

    for _ in range(3):
        page.click("#rerender")
        time.sleep(1)

    assert page.locator("#plot > .lm-Widget").count() == 1
    assert page.locator(ready_selector).count() == 1
    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel defined" in err.lower() for err in errors)
