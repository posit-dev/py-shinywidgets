from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
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


def test_mols2grid_express(page: Page, local_app: ShinyAppProc) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # Express renders through auto_output_ui(); the output id is the function name
    cells = page.locator("#grid .m2g-cell:not(.m2g-phantom)")
    expect(cells).to_have_count(6, timeout=TIMEOUT)
    expect(cells.first).to_contain_text("mol-0")

    # mols2grid binds its cell handlers in initOnUpdate(), which appends
    # phantom filler cells last -- so a phantom cell means handlers are bound
    page.locator("#grid .m2g-phantom").first.wait_for(state="attached", timeout=TIMEOUT)

    # Selection still round-trips to Python through the Express output
    expect(page.locator("#selection")).to_have_text("{}")
    cells.first.click()
    expect(page.locator("#selection")).to_have_text("{0: 'CCO'}")

    assert_no_unexpected_errors(
        errors, failed_requests, allowed_errors=MOLS2GRID_ALLOWED_ERRORS
    )
