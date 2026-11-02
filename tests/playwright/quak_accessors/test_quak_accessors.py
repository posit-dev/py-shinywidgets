from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_quak_accessors_follow_sorting_and_brushing(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#short .quak tbody tr").first).to_be_visible(timeout=30000)
    # The seeded query (no req() guard needed) and all rows
    expect(page.locator("#sql")).to_contain_text('FROM "df"', timeout=30000)
    expect(page.locator("#n_rows")).to_have_text("500")

    # Sorting updates the query (real gesture; selector from render_quak)
    page.locator("#short .quak .sort-button").nth(2).dispatch_event("mousedown")
    expect(page.locator("#sql")).to_contain_text('ORDER BY "value"', timeout=30000)

    # Brushing a numeric column's histogram filters the query and the data.
    # quak renders a brushable histogram (an inline SVG with a brush overlay)
    # in each numeric column's header.
    hist = page.locator("#short .quak thead .interval-x .overlay").first
    box = hist.bounding_box()
    assert box is not None
    y = box["y"] + box["height"] / 2
    page.mouse.move(box["x"] + 5, y)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * 0.5, y, steps=10)
    page.mouse.up()
    expect(page.locator("#sql")).to_contain_text("WHERE", timeout=30000)
    expect(page.locator("#n_rows")).not_to_have_text("500", timeout=30000)

    # The brush drag fired several updates but the debounce collapsed them:
    # far fewer sql() re-reads than one per mouse step
    assert int(page.locator("#n_sql_reads").inner_text()) < 8
    assert_no_unexpected_errors(errors, failed_requests)
