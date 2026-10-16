from __future__ import annotations

import re
import time

from playwright.sync_api import Page, Route, expect
from shiny.run import ShinyAppProc


def expose_manager(route: Route) -> None:
    response = route.fetch()
    text = response.text()
    original = "const manager = new OutputManager({ loader: shinyRequireLoader });"
    assert original in text
    route.fulfill(
        response=response,
        body=text.replace(
            original,
            "const manager = window.widgetManager = new OutputManager({ loader: shinyRequireLoader });",
        ),
    )


def model_counts(page: Page) -> tuple[int, int]:
    last = None
    for _ in range(40):
        current = int(
            re.sub(r"\D", "", page.locator("#server_widgets").inner_text()) or -1
        )
        if current >= 0 and current == last:
            break
        last = current
        time.sleep(0.25)
    client = page.evaluate("() => Object.keys(window.widgetManager._models).length")
    return (last, client)


def rerender(page: Page, n: int) -> None:
    page.click("#rerender")
    expect(page.locator("#fresh")).to_contain_text(f"btn {n}")


def test_rerenders_do_not_leak_models(page: Page, local_app: ShinyAppProc) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#fresh")).to_contain_text("btn 0")
    expect(page.locator("#cached")).to_contain_text("cached A")
    rerender(page, 1)
    baseline = model_counts(page)
    for n in range(2, 7):
        rerender(page, n)
    assert model_counts(page) == baseline


def test_cached_widget_is_redisplayed_and_still_updatable(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.goto(local_app.url)
    expect(page.locator("#cached")).to_contain_text("cached A")
    page.select_option("#key", "B")
    expect(page.locator("#cached")).to_contain_text("cached B")
    page.select_option("#key", "A")
    expect(page.locator("#cached")).to_contain_text("cached A")

    page.click("#recolor")
    expect(page.locator("#cached button")).to_have_css(
        "background-color", "rgb(0, 128, 0)"
    )
