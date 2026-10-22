from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

BOX_HEIGHT_JS = (
    """(sel) => document.querySelector(sel).getBoundingClientRect().height"""
)

# The grid's content box inside the card: its height minus padding (and
# border), i.e., the space the output is meant to fill
CARD_CONTENT_HEIGHT_JS = """() => {
  const body = document.querySelector('#fill_card .card-body');
  const cs = getComputedStyle(body);
  return body.getBoundingClientRect().height
    - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
}"""


def test_ipydatagrid_renders_data(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#grid .lm-DataGrid")).to_have_count(1, timeout=30000)
    expect(page.locator("#grid canvas").first).to_be_visible()
    page.wait_for_function(f"() => ({CANVAS_HAS_PIXELS_JS})('#grid')", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipydatagrid_fills_fixed_height_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#grid .lm-DataGrid")).to_have_count(1, timeout=30000)

    # The grid's own default is a fixed 500px, so check the card (400px) both
    # shrinks the grid below that and, once enlarged, grows it beyond it
    for card_height in (400, 250, 700):
        page.evaluate(
            "(h) => { document.querySelector('#fill_card').style.height = h + 'px'; }",
            card_height,
        )
        page.wait_for_function(
            """() => {
              const out = document.querySelector('#grid').getBoundingClientRect().height;
              const grid = document.querySelector('#grid .lm-DataGrid').getBoundingClientRect().height;
              const avail = (%s)();
              return Math.abs(out - avail) <= 1 && Math.abs(grid - avail) <= 1;
            }"""
            % CARD_CONTENT_HEIGHT_JS,
            timeout=10000,
        )

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipydatagrid_respects_explicit_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#grid_fixed .lm-DataGrid")).to_have_count(1, timeout=30000)
    expect(page.locator("#grid_widget_height .lm-DataGrid")).to_have_count(1)

    # output_widget(height="250px"): the grid fits inside the output (rather
    # than keeping its own 500px default and being clipped)
    page.wait_for_function(
        "() => Math.abs(document.querySelector('#grid_fixed .lm-DataGrid')"
        ".getBoundingClientRect().height - 250) <= 1"
    )
    assert abs(page.evaluate(BOX_HEIGHT_JS, "#grid_fixed") - 250) <= 1

    # DataGrid(layout={"height": "300px"}): the widget's height is used as-is
    assert abs(page.evaluate(BOX_HEIGHT_JS, "#grid_widget_height") - 300) <= 1
    assert (
        abs(page.evaluate(BOX_HEIGHT_JS, "#grid_widget_height .lm-DataGrid") - 300) <= 1
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipydatagrid_selection_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#selections")).to_have_text("[]", timeout=30000)
    expect(page.locator("#grid .lm-DataGrid")).to_have_count(1)
    viewport = page.locator("#grid .lm-DataGrid-viewport")
    box = viewport.bounding_box()
    assert box is not None

    # Cells are drawn on a canvas, so click by coordinate: past the row-header
    # column (64px) and the column header (20px), each row is 20px tall
    page.mouse.click(box["x"] + 100, box["y"] + 70)
    expect(page.locator("#selections")).to_have_text(
        "[{'r1': 2, 'r2': 2, 'c1': 0, 'c2': 0}]", timeout=10000
    )
    page.mouse.click(box["x"] + 170, box["y"] + 92)
    expect(page.locator("#selections")).to_have_text(
        "[{'r1': 3, 'r2': 3, 'c1': 1, 'c2': 1}]", timeout=10000
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipydatagrid_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#grid .lm-DataGrid")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator("#grid .lm-DataGrid")).to_have_count(1)
        expect(page.locator("#selections")).to_have_text("[]")

    # Views of the replaced grids must be disposed (no accumulation): only the
    # three grids on the page (grid, grid_fixed, grid_widget_height) are live
    grid_models = [m for m in client_models(page) if m["name"] == "DataGridModel"]
    assert sum(m["views"] for m in grid_models) == 3
    expect(page.locator(".lm-DataGrid")).to_have_count(3)

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
