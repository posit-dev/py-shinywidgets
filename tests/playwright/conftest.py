from __future__ import annotations

import time

from playwright.sync_api import Page
from shiny.run import ShinyAppProc


def collect_browser_errors(page: Page) -> list[str]:
    errors: list[str] = []

    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    return errors


def assert_no_browser_errors(errors: list[str], forbidden_substrings: list[str]) -> None:
    lower_errors = [err.lower() for err in errors]
    for forbidden in forbidden_substrings:
        needle = forbidden.lower()
        assert not any(needle in err for err in lower_errors), (
            f"Found browser error containing '{forbidden}': {errors}"
        )


def assert_rerender_cleanup(page: Page, local_app: ShinyAppProc, ready_selector: str) -> None:
    errors = collect_browser_errors(page)

    page.goto(local_app.url)
    page.wait_for_selector(ready_selector, timeout=30000)

    for _ in range(3):
        page.click("#rerender")
        time.sleep(1)

    assert page.locator("#plot > .lm-Widget").count() == 1
    assert page.locator(ready_selector).count() == 1
    assert_no_browser_errors(errors, ["widget is not attached", "no comm channel defined"])
