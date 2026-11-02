from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_altair_accessors_follow_real_gestures(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#brush_kind")).to_have_text("IntervalSelection", timeout=30000)
    expect(page.locator("#brushed_rows")).to_have_text("")
    expect(page.locator("#bar_rows")).to_have_text("")

    canvas = page.locator("#brush_chart canvas, #brush_chart svg").first
    box = canvas.bounding_box()
    assert box is not None
    y = box["y"] + box["height"] * 0.4
    page.mouse.move(box["x"] + box["width"] * 0.35, y)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * 0.6, y, steps=8)
    page.mouse.up()
    expect(page.locator("#brushed_rows")).not_to_have_text("", timeout=5000)
    rows = [int(r) for r in page.locator("#brushed_rows").inner_text().split(",")]
    assert rows == list(range(rows[0], rows[-1] + 1))  # a contiguous run of days
    assert 0 < rows[0] and rows[-1] < 29

    # The bar for the bin [2, 3) (holds 2.0 and 2.4; 3.3 is in the next bin)
    bars = page.locator("#bar_chart .mark-rect path, #bar_chart canvas")
    expect(bars.first).to_be_visible(timeout=10000)
    bar_box = page.locator("#bar_chart canvas, #bar_chart svg").first.bounding_box()
    assert bar_box is not None
    # The middle of the x axis (domain [0, 5]) is the bin [2, 3)
    page.mouse.click(
        bar_box["x"] + bar_box["width"] * 0.5, bar_box["y"] + bar_box["height"] * 0.8
    )
    # Half-open bins: 3.3 belongs to the next bar
    expect(page.locator("#bar_rows")).to_have_text("2.0,2.4", timeout=5000)
    assert_no_unexpected_errors(errors, failed_requests)
