from __future__ import annotations

import json
import time
from typing import Any

from playwright.sync_api import Browser, Page, expect
from shiny.run import ShinyAppProc


def read_probe(page: Page) -> dict[str, Any]:
    last = None
    for _ in range(60):
        try:
            current = json.loads(page.locator("#probe").inner_text())
        except json.JSONDecodeError:
            current = None
        if current is not None and current == last:
            return current
        last = current
        time.sleep(0.25)
    assert last is not None
    return last


def open_and_exercise_session(browser: Browser, url: str) -> dict[str, Any]:
    """
    Open a fresh page (a new Shiny session), touch every output (so its widgets
    and the session_lifetime() cache actually get constructed), read the
    server-side probe once it settles, then close the page (ending the
    session).
    """
    page = browser.new_page()
    try:
        page.goto(url)
        expect(page.locator("#r")).to_contain_text("r 0")
        page.click("#rerender")
        expect(page.locator("#r")).to_contain_text("r 1")
        expect(page.locator("#s")).to_contain_text("session-owned")
        page.select_option("#key", "B")
        expect(page.locator("#c")).to_contain_text("cached B")
        page.select_option("#key", "A")
        expect(page.locator("#c")).to_contain_text("cached A")
        return read_probe(page)
    finally:
        page.close()


def test_session_churn_drains_global_state(
    browser: Browser, local_app: ShinyAppProc
) -> None:
    # One session's own settled state: a comm manager, a session widget map
    # entry, one render-owned entry (output `r`'s current, not-yet-invalidated
    # render), and nothing kept (this app has no borrowed-reference pattern).
    baseline = open_and_exercise_session(browser, local_app.url)
    assert baseline["comm_managers"] == 1
    assert baseline["session_widget_id_map"] == 1
    assert baseline["render_owned_widgets"] == 1
    assert baseline["kept_widgets"] == 0

    # Shiny invalidates a session's output Contexts *after* its on_ended
    # cleanup runs; opening and closing many sessions in a row exercises that
    # exact ordering, which per-session cleanup must survive without leaking.
    for _ in range(9):
        open_and_exercise_session(browser, local_app.url)

    # A fresh session, exercised identically, should see exactly one session's
    # worth of state -- not its own plus leftovers from any of the 9 before it.
    final = open_and_exercise_session(browser, local_app.url)
    assert final == baseline
