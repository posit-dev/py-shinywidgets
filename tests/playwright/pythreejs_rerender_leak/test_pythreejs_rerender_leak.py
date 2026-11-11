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


# Synchronous on purpose: wait_for_function() doesn't await an async
# predicate (the promise it returns is truthy, so the wait passes at once)
_MODEL_COUNT_IS_JS = """(expected) =>
    Object.keys(window.widgetManager._models).length === expected
"""

# Holds back the updates in which the browser names models (the light pointing
# at its new target/shadow) until released. comm.ts resolves `Shiny` at call
# time, so wrapping setInputValue after load sees every ShinyComm message.
_HOLD_NAMING_UPDATES_JS = """() => {
    window.__heldUpdates = [];
    const original = Shiny.setInputValue;
    Shiny.setInputValue = (name, value, opts) => {
        if (
            name === 'shinywidgets_comm_send' &&
            JSON.parse(value).header?.msg_type === 'comm_msg' &&
            value.includes('IPY_MODEL_')
        ) {
            window.__heldUpdates.push(() => original(name, value, opts));
            return;
        }
        return original(name, value, opts);
    };
    window.__releaseHeldUpdates = () => {
        Shiny.setInputValue = original;
        window.__heldUpdates.forEach((send) => send());
    };
}"""


def test_models_named_after_their_light_closed_are_collected(
    page: Page, local_app
) -> None:
    """
    When re-renders outpace the browser (a slider drag, a timer), it's still
    creating a render's models after the server has retired that render: the
    light's update naming its new target/shadow then reaches the server after
    the light closed. Held back here to make that ordering deterministic.
    """
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#plot canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")
    page.wait_for_timeout(2000)
    initial = len(client_models(page))

    page.evaluate(_HOLD_NAMING_UPDATES_JS)
    for i in range(1, 3):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        # This render's light has created its models and tried to name them
        page.wait_for_function(f"() => window.__heldUpdates.length === {i}")

    # The first re-render's light is closed by now; its update arrives late
    page.evaluate("() => window.__releaseHeldUpdates()")

    page.wait_for_function(_MODEL_COUNT_IS_JS, arg=initial, timeout=15000)
    assert len(client_models(page)) == initial
