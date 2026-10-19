from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import client_models, expose_manager


# A session-owned widget (constructed once, outside
# any render) whose output is toggled off/on by render.ui. Main never tells
# the view to go away when Shiny unbinds the output -- the detached view keeps
# receiving model updates, and after 5 hide/show cycles the model has 6 live
# views instead of 1. A `shiny:unbound` listener now removes the view.
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
