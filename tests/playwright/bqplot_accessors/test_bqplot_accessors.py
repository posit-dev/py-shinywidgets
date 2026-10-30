from __future__ import annotations

import ast

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def drag(page: Page, box: dict, x0: float, y0: float, x1: float, y1: float) -> None:
    page.mouse.move(box["x"] + box["width"] * x0, box["y"] + box["height"] * y0)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] * x1, box["y"] + box["height"] * y1, steps=10
    )
    page.mouse.up()


def test_selection_follows_brush_drag(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    overlay = page.locator('#fig1 rect[pointer-events="all"]').first
    expect(overlay).to_be_visible(timeout=30000)
    expect(page.locator("#sel1")).to_have_text("[None]", timeout=30000)

    # Brush the left half of the plot
    box = overlay.bounding_box()
    assert box is not None
    drag(page, box, 0.05, 0.05, 0.5, 0.95)

    # The drag streams mid-gesture, but the value settles after the 250ms
    # debounce: the points in the brushed rectangle, one entry per mark
    expect(page.locator("#sel1")).not_to_have_text("[None]", timeout=30000)
    page.wait_for_timeout(500)
    sel = ast.literal_eval(page.locator("#sel1").inner_text())
    assert len(sel) == 1
    assert sel[0] is not None and len(sel[0]) >= 2

    assert_no_unexpected_errors(errors, failed_requests)


def test_brush_reports_the_region(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    overlay = page.locator('#fig2 rect[pointer-events="all"]').first
    expect(overlay).to_be_visible(timeout=30000)
    expect(page.locator("#brush2")).to_have_text("None", timeout=30000)

    # Drag a horizontal interval across part of the x axis
    box = overlay.bounding_box()
    assert box is not None
    drag(page, box, 0.2, 0.5, 0.7, 0.5)

    expect(page.locator("#brush2")).not_to_have_text("None", timeout=30000)
    page.wait_for_timeout(500)
    lo, hi = ast.literal_eval(page.locator("#brush2").inner_text())
    assert 0 <= lo < hi <= 10

    assert_no_unexpected_errors(errors, failed_requests)
