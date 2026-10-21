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


def test_cytoscape_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#graph canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")
    n_canvases = page.locator("#graph canvas").count()

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#graph", timeout=30000)

    # Re-rendering replaces the widget; the retired views must be disposed
    expect(page.locator("#graph .lm-Widget")).to_have_count(1)
    expect(page.locator("#graph canvas")).to_have_count(n_canvases)
    cytoscape_views = [
        m["views"] for m in client_models(page) if m["name"] == "CytoscapeModel"
    ]
    assert sum(cytoscape_views) == 1

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
