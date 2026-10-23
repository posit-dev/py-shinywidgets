from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_plotly_config_tuple_hides_modebar(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # both plots render
    expect(page.locator("#no_modebar .js-plotly-plot")).to_have_count(1, timeout=30000)
    expect(page.locator("#with_modebar .js-plotly-plot")).to_have_count(
        1, timeout=30000
    )

    # displayModeBar: False hides the modebar; the default plot keeps it
    expect(page.locator("#no_modebar .modebar")).to_be_hidden()
    expect(page.locator("#with_modebar .modebar")).not_to_be_hidden()

    assert_no_unexpected_errors(errors, failed_requests)
