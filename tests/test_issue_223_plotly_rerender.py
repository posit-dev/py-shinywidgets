from __future__ import annotations

import time

import pytest
from playwright.sync_api import Page, sync_playwright


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = context.new_page()
    yield page
    context.close()


def test_plotly_rerender_does_not_log_cleanup_errors(
    plotly_rerender_app, page: Page
) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(plotly_rerender_app.url, wait_until="domcontentloaded")
    page.wait_for_selector("#plot .js-plotly-plot", timeout=30000)

    for _ in range(3):
        page.click("#rerender")
        time.sleep(1)

    assert page.locator("#plot .js-plotly-plot").count() == 1
    assert not any("widget is not attached" in err.lower() for err in errors)
