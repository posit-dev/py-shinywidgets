from __future__ import annotations

import time

from playwright.sync_api import Page


def test_plotly_rerender_does_not_log_cleanup_errors(rerender_page: Page) -> None:
    errors: list[str] = []
    rerender_page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    rerender_page.on("pageerror", lambda err: errors.append(str(err)))

    for _ in range(3):
        rerender_page.click("#rerender")
        time.sleep(1)

    assert rerender_page.locator("#plot .js-plotly-plot").count() == 1
    assert not any("widget is not attached" in err.lower() for err in errors)
