from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import client_models, expose_manager

N = 8


# Re-rendering an ipyleaflet map throws an uncaught
# page error per re-render ("Widget is not attached", from Lumino's detach()
# throwing when ipyleaflet's own teardown already pulled the node out of the
# DOM) and leaks the map's view tree (the native Leaflet map, its listeners,
# and its marker/control child views are never released). Also covers the (already-working-on-main) case that a session-
# owned child widget shared across container re-renders keeps exactly one
# live view instead of accumulating one per re-render.
def test_container_rerender_has_no_errors_and_bounded_views(
    page: Page, local_app
) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.route("**/output.js", expose_manager)

    page.goto(local_app.url)
    page.wait_for_selector("#box .widget-button", timeout=15000)
    page.wait_for_selector("#map .leaflet-marker-icon", timeout=15000)

    for i in range(1, N + 1):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator("#box").get_by_text(f"render {i}")).to_have_count(1)
        expect(page.locator("#map .leaflet-container")).to_have_count(1)

    page.wait_for_timeout(500)

    models = client_models(page)
    button_views = [m["views"] for m in models if m["name"] == "ButtonModel"]
    assert button_views == [1], (
        f"shared button view count should stay 1, got {button_views}"
    )

    assert not errors, f"Unexpected console/page errors: {errors}"
