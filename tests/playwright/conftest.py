from __future__ import annotations

from playwright.sync_api import Page, Route, expect
from shiny.run import ShinyAppProc


def open_lifecycle_page(
    page: Page, local_app: ShinyAppProc, url: str | None = None
) -> Page:
    """
    Open an app page with the served output bundle's lifecycle controller
    exposed for test instrumentation (route-local only; no production global).
    """

    def expose_lifecycle(route: Route) -> None:
        response = route.fetch()
        text = response.text()
        original = "const lifecycle = createWidgetLifecycle();"
        assert text.count(original) == 1
        route.fulfill(
            response=response,
            body=text.replace(
                original,
                "const lifecycle = window.widgetLifecycle = createWidgetLifecycle();",
            ),
        )

    page.route("**/output.js", expose_lifecycle)
    page.goto(url or local_app.url)
    page.wait_for_function("!!window.widgetLifecycle")
    return page


def assert_rerender_cleanup(
    page: Page,
    local_app: ShinyAppProc,
    ready_selector: str,
) -> None:
    errors: list[str] = []

    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    page.wait_for_selector(ready_selector, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    expect(page.locator("#plot > .lm-Widget")).to_have_count(1)
    expect(page.locator(ready_selector)).to_have_count(1)
    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel defined" in err.lower() for err in errors)
