from __future__ import annotations

import re
import time

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc


def server_widget_count(page: Page) -> int:
    last = None
    for _ in range(40):
        current = int(
            re.sub(r"\D", "", page.locator("#server_widgets").inner_text()) or -1
        )
        if current >= 0 and current == last:
            return current
        last = current
        time.sleep(0.25)
    assert last is not None
    return last


def test_borrowed_child_dropped_by_container_does_not_leak(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.goto(local_app.url)
    expect(page.locator("#out")).to_contain_text("child 0")

    # One re-render to reach steady state: the sweep always keeps the
    # currently-referenced child (and its lazily materialized Layout/Style)
    # until the *next* sweep rechecks it, so the model count is one render
    # behind, not necessarily flat from the very first render.
    page.click("#rerender")
    expect(page.locator("#out")).to_contain_text("child 1")
    baseline = server_widget_count(page)

    for n in range(2, 8):
        page.click("#rerender")
        expect(page.locator("#out")).to_contain_text(f"child {n}")

    # If kept widgets weren't re-checked, the dropped child from each render
    # would be kept forever, so the count grows by a few models per render instead
    # of holding steady.
    assert server_widget_count(page) == baseline
