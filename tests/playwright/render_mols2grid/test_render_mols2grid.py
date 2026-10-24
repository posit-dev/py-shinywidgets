from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The grid document loads list.js, jQuery, RDKit MinimalLib and Bootstrap from
# CDNs, so first paint can take a while
TIMEOUT = 60000


def wait_for_cells(page: Page, n: int = 12) -> None:
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


def matching_items(page: Page) -> int:
    # The iframe registers its list.js instance on the parent window
    return page.evaluate(
        "Object.values(window.mols2grid_lists)[0].matchingItems.length"
    )


def test_mols2grid_renders_grid(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    wait_for_cells(page)
    frame = page.frame_locator("#grid iframe")
    expect(frame.locator(".m2g-cell:not(.m2g-phantom)").first).to_contain_text("mol-0")
    # The widget half of the composite registers the model on the window
    page.wait_for_function(
        "Object.keys(window).some((k) => k.startsWith('_MOLS2GRID_shiny-'))"
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_mols2grid_selection_reaches_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_cells(page)
    wait_for_cell_handlers(page)

    expect(page.locator("#selection")).to_have_text("{}")
    frame = page.frame_locator("#grid iframe")
    # The checkbox input is visually hidden; clicking the cell toggles it
    frame.locator(".m2g-cell:not(.m2g-phantom)").first.click()
    expect(page.locator("#selection")).to_have_text("{0: 'CCO'}")
    # Deselecting goes back to empty
    frame.locator(".m2g-cell:not(.m2g-phantom)").first.click()
    expect(page.locator("#selection")).to_have_text("{}")

    assert_no_unexpected_errors(errors, failed_requests)


def test_mols2grid_filter_from_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_cells(page)

    assert matching_items(page) == 12
    page.click("#filter")
    page.wait_for_function(
        "Object.values(window.mols2grid_lists)[0].matchingItems.length === 7"
    )
    frame = page.frame_locator("#grid iframe")
    expect(frame.locator(".m2g-cell:not(.m2g-phantom):visible")).to_have_count(7)

    assert_no_unexpected_errors(errors, failed_requests)


def test_mols2grid_rerender_keeps_one_iframe(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_cells(page)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old_iframe = page.locator("#grid iframe").element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_iframe)
        wait_for_cells(page)

    expect(page.locator("#grid iframe")).to_have_count(1)

    assert_no_unexpected_errors(errors, failed_requests)
