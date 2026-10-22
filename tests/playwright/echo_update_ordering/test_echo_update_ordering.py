from __future__ import annotations

from playwright.sync_api import Page, expect


def test_stale_echo_updates_are_dropped(page: Page, local_app) -> None:
    """
    Python answers each browser update with an `echo_update`. When the browser
    writes a trait several times in a row, the echo of an older write arrives
    after the newer value is set; the model must drop it (it can only do that if
    the echo names the update it answers) rather than jump back to the old value.
    """
    page.goto(local_app.url)
    page.get_by_test_id("burst").click()

    expect(page.locator("#server_count")).to_have_text("server: 5", timeout=30000)
    # Give any stale echo time to arrive after the server has caught up.
    page.wait_for_timeout(500)
    expect(page.get_by_test_id("history")).to_have_text("1,2,3,4,5")
