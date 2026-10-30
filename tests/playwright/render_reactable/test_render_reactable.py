from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

pytest.importorskip("reactable")

ROWS = ".ReactTable .rt-tbody .rt-tr-group"


def wait_for_table(page: Page, output_id: str) -> None:
    expect(page.locator(f"#{output_id} .ReactTable")).to_have_count(1, timeout=30000)
    expect(page.locator(f"#{output_id} {ROWS}").first).to_be_visible(timeout=30000)


def test_reactable_renders_styled(page: Page, local_app) -> None:  # noqa: ANN001
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_table(page, "tbl")

    # The renderer ships reactable's stylesheet (it's not part of the widget
    # bundle): the link is served, and the base CSS lays the table out as a
    # flex column (without it, the table renders as stacked, unstyled divs)
    expect(page.locator('link[href*="reactable-py.esm.css"]')).to_have_count(1)
    display = page.locator("#tbl .ReactTable").evaluate(
        "el => getComputedStyle(el).display"
    )
    assert display == "flex"
    # Currency formatting from ColFormat
    expect(page.locator(f"#tbl {ROWS} .rt-td").nth(1)).to_have_text("$1.50")
    # NaN in the data renders as an empty cell (not a serialization error)
    expect(page.locator(f"#tbl {ROWS}").nth(1).locator(".rt-td").nth(1)).to_have_text(
        ""
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_reactable_interactions(page: Page, local_app) -> None:  # noqa: ANN001
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_table(page, "tbl")

    # Sort by name (descending on second click)
    header = page.locator("#tbl .ReactTable .rt-th", has_text="name").first
    header.click()
    header.click()
    expect(page.locator(f"#tbl {ROWS} .rt-td").first).to_have_text("zeta")

    # Per-column filter
    filt = (
        page.locator("#tbl .ReactTable .rt-thead .rt-tr").nth(1).locator("input").first
    )
    filt.fill("alp")
    expect(page.locator(f"#tbl {ROWS}")).to_have_count(1)

    # Pagination reflects the filter
    expect(page.locator("#tbl .ReactTable .rt-page-info")).to_have_text("1–1 of 1 rows")

    assert_no_unexpected_errors(errors, failed_requests)


def test_reactable_inplace_props_update(page: Page, local_app) -> None:  # noqa: ANN001
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_table(page, "tbl")
    expect(page.locator(f"#tbl {ROWS}")).to_have_count(4)

    page.locator("#page_size").fill("2")
    page.locator("#page_size").press("Enter")
    expect(page.locator(f"#tbl {ROWS}")).to_have_count(2)

    assert_no_unexpected_errors(errors, failed_requests)


def test_reactable_rerender(page: Page, local_app) -> None:  # noqa: ANN001
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_table(page, "tbl")

    for _ in range(2):
        page.locator("#rerender").click()
        wait_for_table(page, "tbl")
        # No duplicate tables, still interactive
        expect(page.locator("#tbl .ReactTable")).to_have_count(1)
        expect(page.locator(f"#tbl {ROWS}")).to_have_count(4)

    assert_no_unexpected_errors(errors, failed_requests)


def test_reactable_height_prop_disables_fill(page: Page, local_app) -> None:  # noqa: ANN001
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_table(page, "fixed")

    # The reactable `height=` prop opts out of filling, so the inline height is
    # respected instead of being stretched to the container
    height = page.locator("#fixed .ReactTable").evaluate(
        "el => el.getBoundingClientRect().height"
    )
    assert abs(height - 250) < 2

    assert_no_unexpected_errors(errors, failed_requests)
