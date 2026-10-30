from __future__ import annotations

import ast

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The grid paints cells on a canvas (lumino), so gestures are pixel offsets
# into the viewport: the header row is 20px tall (its center at +10), body
# rows are 20px each starting right below it, and the columns start at
# ~x+75 (`a`, with its menu icon at the header's right edge, x+124), ~x+130
# (`b`), ~x+200 (`c`)
HEADER_Y = 10
ROW_Y = [30 + 20 * r for r in range(20)]
COL_A_X = 100
COL_B_X = 150
COL_A_MENU_X = 124


def viewport_box(page: Page) -> dict:
    vp = page.locator("#grid .lm-DataGrid-viewport").first
    expect(vp).to_be_attached(timeout=30000)
    box = vp.bounding_box()
    assert box is not None
    return box


def click_cell(page: Page, box: dict, x: float, y: float, shift: bool = False) -> None:
    if shift:
        page.keyboard.down("Shift")
    page.mouse.click(box["x"] + x, box["y"] + y)
    if shift:
        page.keyboard.up("Shift")


def sort_a(page: Page, box: dict, direction: str) -> None:
    # A plain header click doesn't sort; sorting lives in the header's menu
    click_cell(page, box, COL_A_MENU_X, HEADER_Y)
    menu = page.locator(".ipydatagrid-context-menu")
    expect(menu).to_be_visible(timeout=5000)
    menu.get_by_text(f"Sort {direction}").click()
    expect(menu).to_be_hidden(timeout=5000)


def test_selections_follows_clicks_and_sort(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#sels")).to_have_text("[]", timeout=30000)
    box = viewport_box(page)

    click_cell(page, box, COL_A_X, ROW_Y[2])
    expect(page.locator("#sels")).to_have_text(
        "[{'r1': 2, 'r2': 2, 'c1': 0, 'c2': 2}]", timeout=30000
    )

    # Shift-click extends the rectangle
    click_cell(page, box, COL_A_X, ROW_Y[5], shift=True)
    expect(page.locator("#sels")).to_have_text(
        "[{'r1': 2, 'r2': 5, 'c1': 0, 'c2': 2}]", timeout=30000
    )

    # Sorting clears the selection
    sort_a(page, box, "Ascending")
    expect(page.locator("#sels")).to_have_text("[]", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_cell_clicked_reports_both_coordinate_spaces(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#sels")).to_have_text("[]", timeout=30000)
    box = viewport_box(page)

    # Sort `a` descending, then click the top body row: visible row 0, data
    # row 19
    sort_a(page, box, "Descending")
    expect(page.locator("#vis")).to_have_text(
        ",".join(str(i) for i in range(19, -1, -1)), timeout=30000
    )
    click_cell(page, box, COL_A_X, ROW_Y[0])
    # The sort gesture's own header click fires cell_clicked too, so wait for
    # the body click specifically (the text round-trips through Python)
    page.wait_for_function(
        """() => document.querySelector('#click').textContent.includes("'region': 'body'")"""
    )
    click = ast.literal_eval(page.locator("#click").inner_text())
    assert click["region"] == "body"
    assert click["row"] == 0
    assert click["primary_key_row"] == 19
    assert click["column"] == "a"

    assert_no_unexpected_errors(errors, failed_requests)


def test_cell_edited_reports_the_edit(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#sels")).to_have_text("[]", timeout=30000)
    box = viewport_box(page)

    # Double-click a cell in column `b`, replace its contents, commit
    page.mouse.dblclick(box["x"] + COL_B_X, box["y"] + ROW_Y[2])
    page.wait_for_timeout(500)
    page.keyboard.press("ControlOrMeta+a")
    page.keyboard.type("edited")
    page.keyboard.press("Enter")

    page.wait_for_function(
        "() => document.querySelector('#edit').textContent.includes('edited')"
    )
    edit = ast.literal_eval(page.locator("#edit").inner_text())
    assert edit["column"] == "b"
    assert edit["value"] == "edited"
    assert edit["row"] == 2  # the data row

    assert_no_unexpected_errors(errors, failed_requests)


def filter_a(page: Page, box: dict, operator: str, value: str) -> None:
    # The header menu's filter-by-condition dialog
    click_cell(page, box, COL_A_MENU_X, HEADER_Y)
    menu = page.locator(".ipydatagrid-context-menu")
    expect(menu).to_be_visible(timeout=5000)
    menu.get_by_text("Filter by condition").click()
    dialog = page.locator(".ipydatagrid-filterMenu")
    expect(dialog).to_be_visible(timeout=5000)
    dialog.locator("select").select_option(operator)
    dialog.locator("input").first.fill(value)
    dialog.locator("button").click()
    expect(dialog).to_be_hidden(timeout=5000)


def test_visible_data_follows_sort_and_filter(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    box = viewport_box(page)

    all_rows = ",".join(str(i) for i in range(20))
    expect(page.locator("#vis")).to_have_text(all_rows, timeout=30000)

    sort_a(page, box, "Descending")
    expect(page.locator("#vis")).to_have_text(
        ",".join(str(i) for i in range(19, -1, -1)), timeout=30000
    )

    filter_a(page, box, ">=", "15")
    expect(page.locator("#vis")).to_have_text("19,18,17,16,15", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_visible_data_returns_no_rows_for_a_zero_match_filter(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    box = viewport_box(page)

    all_rows = ",".join(str(i) for i in range(20))
    expect(page.locator("#vis")).to_have_text(all_rows, timeout=30000)

    # A filter matching nothing, straight from the initial state: the row map
    # stays [] (no _visible_rows change fires), and the widget's own
    # get_visible_data() would return every row -- the accessor must report
    # an empty frame instead
    filter_a(page, box, ">", "100")
    expect(page.locator("#vis")).to_have_text("", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)
