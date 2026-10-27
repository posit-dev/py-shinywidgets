from __future__ import annotations

from playwright.sync_api import Browser, Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# Well under the browser widget manager's 30s model-wait timeout, so a hang on a
# closed singleton fails here instead of passing slowly.
TIMEOUT = 8000


def open_session(browser: Browser, url: str) -> tuple[Page, list[str], list[str]]:
    page = browser.new_page()
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(url)
    return page, errors, failed_requests


def expect_rendered(page: Page, n: int) -> None:
    expect(page.locator("#btn")).to_contain_text(f"vuetify button {n}", timeout=TIMEOUT)
    expect(page.locator("#tmpl")).to_contain_text(
        f"template says render {n}", timeout=TIMEOUT
    )


def rerender(page: Page, n: int) -> None:
    page.click("#rerender")
    expect(page.locator("#render_count")).to_have_text(str(n), timeout=TIMEOUT)
    expect_rendered(page, n)


def test_ipyvuetify_rerenders_and_second_session(
    browser: Browser, local_app: ShinyAppProc
) -> None:
    a, errors_a, failed_a = open_session(browser, local_app.url)
    b = None
    try:
        expect_rendered(a, 0)

        rerender(a, 1)
        models_after_first = len(client_models(a))
        rerender(a, 2)
        rerender(a, 3)
        # The shared theme/template widgets are reused, not re-created per render
        assert len(client_models(a)) == models_after_first, client_models(a)

        b, errors_b, failed_b = open_session(browser, local_app.url)
        expect_rendered(b, 0)
        rerender(b, 1)

        rerender(a, 4)

        for page in (a, b):
            expect(page.locator("#btn .v-theme--dark")).not_to_have_count(
                0, timeout=TIMEOUT
            )

        assert_no_unexpected_errors(errors_a, failed_a)
        assert_no_unexpected_errors(errors_b, failed_b)
    finally:
        a.close()
        if b is not None:
            b.close()
