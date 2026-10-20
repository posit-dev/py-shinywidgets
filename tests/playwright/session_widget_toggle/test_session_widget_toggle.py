from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import client_models, expose_manager


# Regression test: a session-owned widget whose output is toggled off/on by
# render.ui used to keep its detached views alive (6 live views after 5
# cycles); a `shiny:unbound` listener now removes the view on unbind.
def test_session_widget_view_count_stays_bounded_across_toggles(
    page: Page, local_app
) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    page.wait_for_selector("#w .widget-slider", timeout=15000)

    for _ in range(5):
        page.uncheck("#show")
        expect(page.locator("#w")).to_have_count(0)
        page.check("#show")
        page.wait_for_selector("#w .widget-slider", timeout=5000)

    page.wait_for_timeout(300)
    models = client_models(page)
    slider_views = [m["views"] for m in models if m["name"] == "IntSliderModel"]
    assert slider_views == [1], f"expected exactly 1 live view, got {slider_views}"
    assert page.locator(".widget-slider").count() == 1
