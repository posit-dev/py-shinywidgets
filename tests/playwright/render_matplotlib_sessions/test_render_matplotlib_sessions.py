from __future__ import annotations

import re

from playwright.sync_api import Browser, expect
from shiny.run import ShinyAppProc

# Each output's text lists the labels of the lines on its figure (one per
# render, labelled with the drawing session's id)
ONE_LABEL = re.compile(r"^\S+$")


def test_pyplot_current_figure_not_shared_across_sessions(
    browser: Browser, local_app: ShinyAppProc
) -> None:
    session_a = browser.new_page()
    session_b = browser.new_page()
    try:
        session_a.goto(local_app.url)
        expect(session_a.locator("#mpl canvas").first).to_be_visible(timeout=30000)
        expect(session_a.locator("#lines")).to_have_text(ONE_LABEL)
        label_a = session_a.locator("#lines").inner_text()

        # Session B's plt.gca() must not return session A's live figure
        session_b.goto(local_app.url)
        expect(session_b.locator("#mpl canvas").first).to_be_visible(timeout=30000)
        expect(session_b.locator("#mpl")).not_to_contain_text("another Shiny session")
        expect(session_b.locator("#lines")).to_have_text(ONE_LABEL)
        expect(session_b.locator("#lines")).not_to_have_text(label_a)

        # Nor do re-renders draw into the previous render's figure
        session_a.click("#redraw")
        session_a.click("#redraw")
        expect(session_a.locator("#mpl canvas").first).to_be_visible()
        expect(session_a.locator("#lines")).to_have_text(label_a)
        expect(session_b.locator("#lines")).to_have_text(ONE_LABEL)
    finally:
        session_a.close()
        session_b.close()
