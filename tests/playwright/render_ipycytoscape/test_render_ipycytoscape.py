from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)


def test_cytoscape_renders_graph(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#graph canvas").first).to_be_visible(timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#graph", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_cytoscape_node_click_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#clicked")).to_have_text("none", timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#graph", timeout=30000)

    # The grid layout puts the graph's only node at the center of the canvas.
    # Cytoscape reports the tap through a custom comm message, which
    # shinywidgets relays to the callback registered with `widget.on()`.
    page.locator("#graph").click()
    expect(page.locator("#clicked")).to_have_text("solo", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_cytoscape_callbacks_for_several_events_all_fire(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#hovered")).to_have_text("none", timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#graph", timeout=30000)

    # A second event type on the same element type must fire too (ipycytoscape
    # drops it when it's registered after the graph is displayed)
    page.locator("#graph").hover()
    expect(page.locator("#hovered")).to_have_text("solo", timeout=10000)
    page.locator("#graph").click()
    expect(page.locator("#clicked")).to_have_text("solo", timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)


# Settled state of the browser's widget registry after re-renders: exactly one
# CytoscapeModel, with exactly one live view (the retired model's view is
# disposed and the model dropped from the registry). Mirrors client_models()
# in tests/playwright/conftest.py.
CYTOSCAPE_MODELS_SETTLED_JS = """async () => {
    const models = await Promise.all(
        Object.values(window.widgetManager._models).map((p) => p.catch(() => null))
    );
    const cyto = models.filter((m) => m && m.get('_model_name') === 'CytoscapeModel');
    const views = cyto.reduce((n, m) => n + Object.keys(m.views || {}).length, 0);
    return cyto.length === 1 && views === 1;
}"""


def test_cytoscape_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#graph canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")
    n_canvases = page.locator("#graph canvas").count()

    for i in range(1, 4):
        old_canvas = page.locator("#graph canvas").first.element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        # Wait for the retired view's canvas to detach first: until it does,
        # the pixels check below can be satisfied by the *previous* render's
        # canvas (the new view is created asynchronously, so on a slow runner
        # the check would pass before the re-render has actually happened)
        page.wait_for_function("(el) => !el.isConnected", arg=old_canvas)
        page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#graph", timeout=30000)

    # Re-rendering replaces the widget; the retired views must be disposed
    expect(page.locator("#graph .lm-Widget")).to_have_count(1)
    expect(page.locator("#graph canvas")).to_have_count(n_canvases)
    # The retired model's teardown (view disposal, then removal from the
    # manager's registry) is driven by a comm_close that the server sends
    # after the re-render, so it can still be in flight here; wait for the
    # registry to settle rather than sampling it once
    page.wait_for_function(CYTOSCAPE_MODELS_SETTLED_JS, timeout=30000)
    cytoscape_views = [
        m["views"] for m in client_models(page) if m["name"] == "CytoscapeModel"
    ]
    assert sum(cytoscape_views) == 1

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
