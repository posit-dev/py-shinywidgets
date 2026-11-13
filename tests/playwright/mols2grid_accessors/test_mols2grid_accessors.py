from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The widget's frontend fetches the RDKit MinimalLib wasm from a CDN at render
# time, so first paint can take a while (same constraint as the render_mols2grid
# tests)
TIMEOUT = 60000

# mols2grid's proper-widget branch guards its cached-selection restore with
# `cachedSelection.length` (a fixed 2-element array, so always truthy) instead
# of the selection's size, so the restore handler runs on every list.js
# update and its `$('.m2g-cell input[checked="false"]')` query matches
# nothing, logging this (benign) error. Drop this once fixed upstream.
MOLS2GRID_ALLOWED_ERRORS = (
    'Empty selection for query .m2g-cell input[checked="false"]',
)


def wait_for_cells(page: Page, n: int = 3) -> None:
    expect(page.locator("#grid .m2g-cell:not(.m2g-phantom)")).to_have_count(
        n, timeout=TIMEOUT
    )


def wait_for_cell_handlers(page: Page) -> None:
    # mols2grid (re)binds its cell click/keyboard handlers in initOnUpdate(),
    # which runs on list.js's "updated" event (a beat after the cells first
    # paint) and appends phantom filler cells last -- so a phantom cell means
    # the handlers are bound
    page.locator("#grid .m2g-phantom").first.wait_for(state="attached", timeout=TIMEOUT)


def test_selection_and_clicks_reach_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_cells(page)
    wait_for_cell_handlers(page)

    # selected() is seeded empty at render; clicked() is None until a click
    expect(page.locator("#selected")).to_have_text("{}", timeout=TIMEOUT)
    expect(page.locator("#clicked")).to_have_text("", timeout=TIMEOUT)

    cells = page.locator("#grid .m2g-cell:not(.m2g-phantom)")
    # The checkbox input is visually hidden; clicking the cell toggles it
    cells.first.click()
    expect(page.locator("#selected")).to_have_text("{0: 'CCO'}", timeout=TIMEOUT)

    # The per-cell click target (added by clicks=True) is a distinct gesture
    # from the selection checkbox; it posts the row's data to .clicked()
    page.locator("#grid .m2g-cell .m2g-callback").first.click()
    expect(page.locator("#clicked")).to_have_text("mol-0", timeout=TIMEOUT)

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=MOLS2GRID_ALLOWED_ERRORS
    )
