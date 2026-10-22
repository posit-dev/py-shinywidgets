from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

WIDGET_HEIGHT_JS = (
    "() => document.querySelector('#out > .lm-Widget').getBoundingClientRect().height"
)


def test_rerender_from_fill_to_own_height_stops_filling(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # The first render fills its 400px container
    expect(page.locator("#out > .lm-Widget")).to_have_count(1, timeout=10000)
    page.wait_for_function(f"({WIDGET_HEIGHT_JS})() === 400", timeout=10000)

    # A re-render into the same output whose widget has its own height must take
    # that height, not keep the previous render's filling styles
    page.click("#own_height")
    expect(page.locator("#render_count")).to_have_text("1")
    page.wait_for_function(
        "() => document.querySelector('#out > .lm-Widget')?.style.height === '200px'",
        timeout=10000,
    )
    expect(page.locator("#out")).not_to_have_class(
        re.compile(r"\bforward-fill-potential\b")
    )
    assert page.evaluate(WIDGET_HEIGHT_JS) == 200

    assert_no_unexpected_errors(errors, failed_requests)
