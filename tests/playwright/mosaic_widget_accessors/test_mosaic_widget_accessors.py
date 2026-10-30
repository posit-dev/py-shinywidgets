from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def wait_for_plots(page: Page, selector: str) -> None:
    expect(page.locator(f"{selector} .plot svg")).to_have_count(2, timeout=30000)


def test_mosaic_accessors_follow_brushing(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_plots(page, "#dashboard")

    # Nothing brushed yet: empty params, every row selected
    expect(page.locator("#params")).to_have_text("{}", timeout=30000)
    expect(page.locator("#n_selected")).to_have_text("2000")

    # Brush the left third of the top (dot) plot
    box = page.locator("#dashboard .plot svg").first.bounding_box()
    assert box is not None
    x0, y0 = box["x"] + box["width"] * 0.25, box["y"] + box["height"] * 0.25
    page.mouse.move(x0, y0)
    page.mouse.down()
    page.mouse.move(x0 + box["width"] * 0.15, y0 + box["height"] * 0.4, steps=10)
    page.mouse.up()

    expect(page.locator("#params")).to_contain_text("brush", timeout=30000)
    expect(page.locator("#params")).to_contain_text("predicate", timeout=30000)
    expect(page.locator("#n_selected")).not_to_have_text("2000", timeout=30000)
    selected = int(page.locator("#n_selected").inner_text())
    assert 0 < selected < 2000

    # Clicking empty plot area clears the brush; mosaic empties the
    # predicate but keeps the (now inert) brush param
    page.mouse.click(box["x"] + box["width"] * 0.9, box["y"] + box["height"] * 0.9)
    expect(page.locator("#params")).to_have_text(
        "{'brush': {'predicate': ''}}", timeout=30000
    )
    expect(page.locator("#n_selected")).to_have_text("2000", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)
