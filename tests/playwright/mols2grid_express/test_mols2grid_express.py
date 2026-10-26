from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The grid document loads list.js, jQuery, RDKit MinimalLib and Bootstrap from
# CDNs, so first paint can take a while
TIMEOUT = 60000


def test_mols2grid_express(page: Page, local_app: ShinyAppProc) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # Express renders through auto_output_ui(); the output id is the function name
    frame = page.frame_locator("#grid iframe")
    cells = frame.locator(".m2g-cell:not(.m2g-phantom)")
    expect(cells).to_have_count(6, timeout=TIMEOUT)
    expect(cells.first).to_contain_text("mol-0")

    # Selection still round-trips to Python through the Express output
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
    expect(page.locator("#selection")).to_have_text("{}")
    cells.first.click()
    expect(page.locator("#selection")).to_have_text("{0: 'CCO'}")

    assert_no_unexpected_errors(errors, failed_requests)
