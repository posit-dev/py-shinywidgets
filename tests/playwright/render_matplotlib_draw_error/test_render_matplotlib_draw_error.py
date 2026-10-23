from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc


def test_draw_error_is_an_output_error(page: Page, local_app: ShinyAppProc) -> None:
    page.goto(local_app.url)

    # Shown like any other render error, rather than disconnecting the session
    expect(page.locator("#bad.shiny-output-error")).to_contain_text(
        "badcommand", timeout=30000
    )
    expect(page.locator("#good canvas").first).to_be_visible()

    page.click("#bump")
    expect(page.locator("#count")).to_have_text("1")
    expect(page.locator("#shiny-disconnected-overlay")).to_have_count(0)
