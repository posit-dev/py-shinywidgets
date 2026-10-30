from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)


def click_at(page: Page, x: float, y: float) -> None:
    # The app places nodes at preset layout coordinates, which cytoscape maps
    # 1:1 onto the canvas (padding=0)
    box = page.locator("#graph canvas").first.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + x, box["y"] + y)


def goto_drawn(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#graph canvas").first).to_be_visible(timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#graph", timeout=30000)


def test_node_and_edge_clicks(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_drawn(page, local_app)
    expect(page.locator("#node")).to_have_text("None")
    expect(page.locator("#edge")).to_have_text("None")

    click_at(page, 100, 175)  # node "a"
    expect(page.locator("#node")).to_have_text("a", timeout=10000)

    click_at(page, 200, 175)  # the midpoint of edge a-b
    expect(page.locator("#edge")).to_have_text("a->b", timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_clicks_still_fire_after_rerender(page: Page, local_app) -> None:
    # Regression test for the eager attach: ipycytoscape's frontend silently
    # drops click registrations made after the view exists, so a lazy
    # (first-read) registration would never fire after a re-render
    errors, failed_requests = collect_errors(page)
    goto_drawn(page, local_app)

    click_at(page, 100, 175)  # node "a"
    expect(page.locator("#node")).to_have_text("a", timeout=10000)

    page.click("#rerender")
    expect(page.locator("#node")).to_have_text("None", timeout=10000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#graph", timeout=30000)
    page.wait_for_timeout(1000)  # let the new view's layout settle

    click_at(page, 300, 175)  # node "b"
    expect(page.locator("#node")).to_have_text("b", timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)
