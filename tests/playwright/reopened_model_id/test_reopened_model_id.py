from __future__ import annotations

from playwright.sync_api import Page, expect


# When a widget is assigned an explicit model id, re-rendering closes the old
# widget and opens a new one with the same comm id. The close is sent
# on_flushed (after the new comm's open), so the browser would look the model
# up by id and tear down the *new* model -- unless the close is suppressed at
# send time because the id has been re-registered by a newer comm.
def test_reopened_model_id_still_renders(page: Page, local_app) -> None:
    page.goto(local_app.url)
    page.wait_for_selector("#slider .widget-slider", timeout=15000)

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator("#slider .widget-slider")).to_have_count(1)
        expect(page.locator("#slider").get_by_text(f"render {i}")).to_have_count(1)
