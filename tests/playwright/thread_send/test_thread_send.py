"""
Widget updates made from a worker thread (nglview's remote-call thread, a user's
own threading.Thread) must reach the browser promptly: py-shiny's flush request
is thread-safe, and ShinyComm.send() must stay on that path.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_update_from_worker_thread_reaches_browser(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    readout = page.locator("#slider .widget-readout")
    expect(readout).to_have_text("1", timeout=30000)

    page.click("#go")
    expect(readout).to_have_text("42", timeout=5000)

    assert_no_unexpected_errors(errors, failed_requests)
