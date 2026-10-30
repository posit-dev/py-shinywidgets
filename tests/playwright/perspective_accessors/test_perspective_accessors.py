from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Perspective ships a large (~6MB) ESM bundle inline in the widget state and
# compiles its WASM engine on first render, so allow generous timeouts
VIEWER = "#grid perspective-viewer"


def test_perspective_accessors_follow_viewer_edits(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    viewer = page.locator(VIEWER)
    # the datagrid renders cells into (nested) shadow roots, which
    # playwright's css/text engines pierce by default
    expect(viewer.locator("td", has_text="A").first).to_be_visible(timeout=60000)
    expect(page.locator("#filter_out")).to_have_text("[]")
    expect(page.locator("#config_out")).to_have_text("sort=[] group_by=[]")

    # Add a filter through the settings panel: drag the column onto the
    # filter field, keep the `==` operator, and type the value. Done first:
    # the drag is unreliable right after a sort re-renders the datagrid.
    page.locator(
        ".column-selector-column", has_text="category"
    ).locator(".column-selector-draggable").drag_to(
        page.locator("#top_panel #filter .column-empty-input")
    )
    value_input = page.locator("#top_panel #filter input.string-filter")
    value_input.click()
    value_input.fill("A")
    value_input.press("Enter")
    expect(page.locator("#filter_out")).to_have_text(
        "[['category', '==', 'A']]", timeout=30000
    )
    # ... and the grid actually filtered (30 rows -> the 10 category-A rows)
    expect(viewer.locator("td", has_text="A")).to_have_count(10, timeout=30000)

    # Sorting a column (clicking its header) syncs into view_config()
    viewer.locator("th", has_text="value").first.click()
    expect(page.locator("#config_out")).to_have_text(
        "sort=[['value', 'desc']] group_by=[]", timeout=30000
    )

    # Closing the settings panel is cosmetic: view_config() must not change
    config = page.locator("#config_out").inner_text()
    page.locator("#settings_close_button").click()
    page.wait_for_timeout(1000)
    expect(page.locator("#config_out")).to_have_text(config)

    assert_no_unexpected_errors(errors, failed_requests)
