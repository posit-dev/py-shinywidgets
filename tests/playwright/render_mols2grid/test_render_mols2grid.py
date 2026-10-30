from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The widget's frontend fetches the RDKit MinimalLib wasm from a CDN at render
# time, so first paint can take a while
TIMEOUT = 60000

# mols2grid's proper-widget branch guards its cached-selection restore with
# `cachedSelection.length` (a fixed 2-element array, so always truthy) instead
# of the selection's size, so the restore handler runs on every list.js
# update and its `$('.m2g-cell input[checked="false"]')` query matches
# nothing, logging this (benign) error. Drop this once fixed upstream.
MOLS2GRID_ALLOWED_ERRORS = (
    'Empty selection for query .m2g-cell input[checked="false"]',
)


def wait_for_cells(page: Page, n: int = 12) -> None:
    expect(page.locator("#grid .m2g-cell:not(.m2g-phantom)")).to_have_count(
        n, timeout=TIMEOUT
    )


def wait_for_cell_handlers(page: Page) -> None:
    # mols2grid (re)binds its cell click/keyboard handlers in initOnUpdate(),
    # which runs on list.js's "updated" event (a beat after the cells first
    # paint) and appends phantom filler cells last -- so a phantom cell means
    # the handlers are bound
    page.locator("#grid .m2g-phantom").first.wait_for(state="attached", timeout=TIMEOUT)


def matching_items(page: Page) -> int:
    # The app sets M2G_DEBUG=1, which registers the grid's list.js instance on
    # the window (keyed by grid name)
    return page.evaluate(
        "Object.values(window.__mols2grid__)[0].listObj.matchingItems.length"
    )


def test_mols2grid_renders_grid(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    wait_for_cells(page)
    cells = page.locator("#grid .m2g-cell:not(.m2g-phantom)")
    expect(cells.first).to_contain_text("mol-0")
    # The grid registers its list.js instance on the window. NB: the key is
    # the widget's `name` trait, which mols2grid's proper-widget branch never
    # populates from the grid's name (it stays "default"), so don't assert on
    # the key itself
    page.wait_for_function(
        "window.__mols2grid__ && Object.keys(window.__mols2grid__).length > 0",
        timeout=TIMEOUT,
    )

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=MOLS2GRID_ALLOWED_ERRORS
    )


def test_mols2grid_selection_reaches_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_cells(page)
    wait_for_cell_handlers(page)

    expect(page.locator("#selection")).to_have_text("{}")
    cells = page.locator("#grid .m2g-cell:not(.m2g-phantom)")
    # The checkbox input is visually hidden; clicking the cell toggles it
    cells.first.click()
    expect(page.locator("#selection")).to_have_text("{0: 'CCO'}")
    # Deselecting goes back to empty
    cells.first.click()
    expect(page.locator("#selection")).to_have_text("{}")

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=MOLS2GRID_ALLOWED_ERRORS
    )


def test_mols2grid_filter_from_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_cells(page)

    assert matching_items(page) == 12
    page.click("#filter")
    page.wait_for_function(
        "Object.values(window.__mols2grid__)[0].listObj.matchingItems.length === 7"
    )
    expect(page.locator("#grid .m2g-cell:not(.m2g-phantom):visible")).to_have_count(7)

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=MOLS2GRID_ALLOWED_ERRORS
    )


def test_mols2grid_rerender_replaces_the_widget(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_cells(page)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old_widget = page.locator("#grid [id^='widget-m2g-']").element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_widget)
        wait_for_cells(page)

    expect(page.locator("#grid [id^='widget-m2g-']")).to_have_count(1)

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=MOLS2GRID_ALLOWED_ERRORS
    )
