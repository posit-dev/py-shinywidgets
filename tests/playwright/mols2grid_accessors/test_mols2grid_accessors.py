from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The grid document loads list.js, jQuery, RDKit MinimalLib and Bootstrap from
# CDNs, so first paint can take a while (same constraint as the existing
# render_mols2grid tests)
TIMEOUT = 60000


def wait_for_cells(page: Page, n: int = 3) -> None:
    frame = page.frame_locator("#grid iframe")
    expect(frame.locator(".m2g-cell:not(.m2g-phantom)")).to_have_count(
        n, timeout=TIMEOUT
    )


def wait_for_cell_handlers(page: Page) -> None:
    # mols2grid (re)binds its cell click/keyboard handlers on list.js's
    # "updated" event, which fires a beat after the cells first paint
    page.wait_for_function(
        """
        (() => {
          const doc = document.querySelector('#grid iframe').contentDocument;
          if (!doc) return false;
          const cell = doc.querySelector('#mols2grid .m2g-cell');
          if (!cell) return false;
          const jq = doc.defaultView.jQuery;
          return !!(jq && jq._data(cell, 'events') && jq._data(cell, 'events').click);
        })()
        """,
        timeout=TIMEOUT,
    )


def test_selection_and_clicks_reach_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_cells(page)
    wait_for_cell_handlers(page)

    # selection() is seeded empty at render; clicked() is None until a click
    expect(page.locator("#selected")).to_have_text("{}", timeout=TIMEOUT)
    expect(page.locator("#clicked")).to_have_text("", timeout=TIMEOUT)

    # The checkbox input is visually hidden; clicking the cell toggles it
    frame = page.frame_locator("#grid iframe")
    frame.locator(".m2g-cell:not(.m2g-phantom)").first.click()
    expect(page.locator("#selected")).to_have_text("{0: 'CCO'}", timeout=TIMEOUT)

    # The per-cell click target (added by clicks=True) is a distinct gesture
    # from the selection checkbox; it posts the row's data to .clicked()
    frame.locator(".m2g-cell .m2g-callback").first.click()
    expect(page.locator("#clicked")).to_have_text("mol-0", timeout=TIMEOUT)

    assert_no_unexpected_errors(errors, failed_requests)
