from __future__ import annotations

from playwright.sync_api import Browser, expect
from shiny.run import ShinyAppProc

# Before the fix, a foreign-session widget leaves the output "recalculating" for
# a 30s client-side timeout instead of erroring. Keep this well under that so a
# failing (pre-fix) run reports quickly instead of waiting it out.
ERROR_TIMEOUT = 5000


def test_cross_session_widget_is_rejected_not_hung(
    browser: Browser, local_app: ShinyAppProc
) -> None:
    session_a = browser.new_page()
    try:
        session_a.goto(local_app.url)
        expect(session_a.locator("#direct .widget-slider")).to_have_count(1)

        session_b = browser.new_page()
        try:
            session_b.goto(local_app.url)

            # A clear, immediate error -- not a blank/"recalculating" output.
            expect(session_b.locator("#direct")).to_contain_text(
                "another Shiny session", timeout=ERROR_TIMEOUT
            )
            expect(session_b.locator("#as_child")).to_contain_text(
                "another Shiny session", timeout=ERROR_TIMEOUT
            )
        finally:
            session_b.close()

        # Session A's own widget is unaffected by session B's rejected render.
        session_a.click("#bump")
        expect(session_a.locator("#direct .widget-readout")).to_have_text("1")
        expect(session_a.locator("#direct .widget-slider")).to_have_count(1)
    finally:
        session_a.close()
