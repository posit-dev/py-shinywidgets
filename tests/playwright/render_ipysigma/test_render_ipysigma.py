from __future__ import annotations

import io

from PIL import Image
from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# Largest allowed gap between a widget's rendered box and its container (px)
TOLERANCE = 1.5
# Sigma's canvases sit inside a 1px border on the widget
BORDER_TOLERANCE = 3

BOX_JS = """(sel) => {
  const r = document.querySelector(sel).getBoundingClientRect();
  return { width: r.width, height: r.height };
}"""


def box(page: Page, selector: str) -> dict[str, float]:
    return page.evaluate(BOX_JS, selector)


def count_node_pixels(page: Page, output: str) -> int:
    # Sigma draws with WebGL, whose pixels can't be read back from the canvas,
    # so screenshot the output and count sigma's default node color (#999)
    png = page.locator(output).screenshot()
    image = Image.open(io.BytesIO(png)).convert("RGB")
    data = image.tobytes()
    return sum(
        1
        for r, g, b in zip(data[0::3], data[1::3], data[2::3])
        if abs(r - 0x99) <= 4 and abs(g - 0x99) <= 4 and abs(b - 0x99) <= 4
    )


def wait_for_graph(page: Page, output: str) -> None:
    expect(page.locator(f"{output} canvas.sigma-nodes")).to_have_count(1, timeout=30000)


def test_ipysigma_renders_graph(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    wait_for_graph(page, "#fills")
    assert count_node_pixels(page, "#fills") > 100
    expect(page.locator("#fills .ipysigma-widget")).to_contain_text("34 nodes")

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipysigma_fills_fillable_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 1800})
    page.goto(local_app.url)
    wait_for_graph(page, "#fills")

    out = box(page, "#fills")
    widget = box(page, "#fills .ipysigma-widget")
    graph = box(page, "#fills canvas.sigma-nodes")
    card = box(page, "#fill_card")

    # The card is shorter than sigma's default 500px, so the graph must shrink to
    # its container (the card minus its padding) rather than overflow it
    assert abs(widget["height"] - out["height"]) <= TOLERANCE, (widget, out)
    assert abs(widget["width"] - out["width"]) <= TOLERANCE, (widget, out)
    assert abs(graph["height"] - out["height"]) <= BORDER_TOLERANCE, (graph, out)
    assert abs(graph["width"] - out["width"]) <= BORDER_TOLERANCE, (graph, out)
    assert out["height"] < card["height"], (card, out)
    assert card["height"] - out["height"] <= 40, (card, out)

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipysigma_respects_explicit_heights(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 1800})
    page.goto(local_app.url)
    wait_for_graph(page, "#fixed_output")
    wait_for_graph(page, "#fixed_widget")

    # output_widget(height="350px")
    assert abs(box(page, "#fixed_output")["height"] - 350) <= TOLERANCE
    assert abs(box(page, "#fixed_output .ipysigma-widget")["height"] - 350) <= TOLERANCE

    # Sigma(..., height=300) inside a taller, filling card
    assert box(page, "#fixed_widget")["height"] > 400
    assert abs(box(page, "#fixed_widget .ipysigma-widget")["height"] - 300) <= TOLERANCE

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipysigma_selected_node_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_graph(page, "#fills")
    expect(page.locator("#selected")).to_have_text("None")

    # Choosing a node in sigma's search box syncs `selected_node` back to Python
    # (browser -> shinywidgets comm -> reactive_read -> UI)
    page.locator("#fills .choices").click()
    page.keyboard.type("12")
    page.keyboard.press("Enter")
    expect(page.locator("#selected")).to_have_text("12", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipysigma_rerender_releases_old_views(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    wait_for_graph(page, "#fills")
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old = page.locator("#fills .ipysigma-widget").element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old)
        wait_for_graph(page, "#fills")

    expect(page.locator("#fills .ipysigma-widget")).to_have_count(1)
    # 3 outputs, each with exactly one live Sigma view; none left from the
    # three re-rendered ones
    live_views = sum(
        m["views"] for m in client_models(page) if m["name"] == "SigmaModel"
    )
    assert live_views == 3, client_models(page)

    assert not any("widget is not attached" in e.lower() for e in errors)
    assert_no_unexpected_errors(errors, failed_requests)


# Sigma draws each view with 3 WebGL contexts. Chrome caps live contexts per page
# (about 16) and evicts the oldest when that's exceeded, so contexts a removed view
# didn't release would eventually blank the other (older) graphs on the page.
LOST_CONTEXTS_JS = """(sel) => {
  let lost = 0;
  for (const c of document.querySelectorAll(`${sel} canvas`)) {
    const gl = c.getContext('webgl2') ?? c.getContext('webgl');
    if (gl?.isContextLost()) lost++;
  }
  return lost;
}"""


def test_ipysigma_rerender_keeps_other_graphs_drawn(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    for output in ("#fills", "#fixed_output", "#fixed_widget"):
        wait_for_graph(page, output)

    # Re-render the newest graph, so leaked contexts would evict the older,
    # still-live ones
    for i in range(1, 5):
        old = page.locator("#fixed_widget .ipysigma-widget").element_handle()
        page.click("#rerender_last")
        expect(page.locator("#render_last_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old)
        wait_for_graph(page, "#fixed_widget")

    for output in ("#fills", "#fixed_output", "#fixed_widget"):
        assert page.evaluate(LOST_CONTEXTS_JS, output) == 0, output

    assert_no_unexpected_errors(errors, failed_requests)
