from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors
from tests.playwright.embedding_atlas_accessors.app import docs


def unexpected_errors(errors: list[str]) -> list[str]:
    # Chromium's headless build has no WebGPU, so the embedding view itself
    # (but not the rest of the explorer) logs "Could not get WebGPU ..."
    return [e for e in errors if "WebGPU" not in e]


def bar(page: Page, label: str):
    # Chart bar labels, unlike table cells, are `flex-none` elements
    return page.locator("#atlas div.flex-none", has_text=re.compile(rf"^{label}$"))


def test_predicate_reports_the_filter(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#pred")).to_have_text("None", timeout=30000)

    # Clicking a bar in the "group" chart filters the data (headless Chromium
    # can't render the WebGPU embedding view, so filter via the bar chart)
    bar(page, "c").click()
    expect(page.locator("#pred")).to_contain_text(
        "IS NOT DISTINCT FROM 'c'", timeout=30000
    )

    # Shift-clicking another bar ORs it into the predicate
    page.keyboard.down("Shift")
    bar(page, "a").click()
    page.keyboard.up("Shift")
    expect(page.locator("#pred")).to_contain_text("OR", timeout=30000)

    assert_no_unexpected_errors(unexpected_errors(errors), failed_requests)


def test_selection_returns_filtered_rows(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#nsel")).to_have_text("300", timeout=30000)

    bar(page, "c").click()
    expected = int((docs["group"] == "c").sum())
    assert 0 < expected < len(docs)
    expect(page.locator("#nsel")).to_have_text(str(expected), timeout=30000)

    assert_no_unexpected_errors(unexpected_errors(errors), failed_requests)
