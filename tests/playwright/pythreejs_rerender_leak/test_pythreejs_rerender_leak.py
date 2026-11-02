from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)


def test_rerender_does_not_leak_browser_created_models(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#plot canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")
    page.wait_for_timeout(2000)

    def model_count() -> int:
        return len(client_models(page))

    initial = model_count()
    # The scene's DirectionalLight has browser-created target/shadow models
    names = {m["name"] for m in client_models(page)}
    assert "DirectionalLightShadowModel" in names
    assert "Object3DModel" in names

    for i in range(1, 3):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_timeout(2000)

    # ~3 browser-created models (target, shadow, shadow camera) used to leak
    # per re-render
    assert model_count() == initial

    # The upstream "Error setting state" noise (pythreejs registers listeners
    # on the "uninitialized" string sentinel) predates this fix; what must not
    # appear is the close-time error its sibling causes
    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=("Error setting state",)
    )
