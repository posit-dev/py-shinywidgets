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
    snapshot_id: str | None = None,
) -> None:
    errors: list[str] = []
    startup_errors: list[str] = []
    collecting_cleanup = False

    def record_error(message: str) -> None:
        (errors if collecting_cleanup else startup_errors).append(message)

    page.on(
        "console",
        lambda msg: record_error(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: record_error(str(err)))
    page.on(
        "response",
        lambda response: (
            record_error(f"HTTP {response.status}: {response.url}")
            if response.status >= 400
            else None
        ),
    )

    open_lifecycle_page(page, local_app)
    page.wait_for_selector(ready_selector, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")
    page.wait_for_function(
        "() => document.querySelector('#plot').dataset.shinywidgetsModelId"
    )
    baseline: str | None = None
    if snapshot_id is not None:
        page.wait_for_function(
            """id => {
                const text = document.getElementById(id).textContent;
                const counts = /^records=(\\d+) comms=(\\d+) leases=(\\d+)$/.exec(text);
                return counts && Number(counts[1]) > 0 && Number(counts[2]) > 0
                    && Number(counts[3]) === 1;
            }""",
            arg=snapshot_id,
        )
        baseline = page.locator(f"#{snapshot_id}").inner_text()
    browser_baseline = browser_widget_counts(page, ["#plot"])

    assert not any("widget is not attached" in err.lower() for err in startup_errors)
    assert not any("no comm channel defined" in err.lower() for err in startup_errors)
    if startup_errors:
        print("Widget startup diagnostics:", startup_errors)
    collecting_cleanup = True

    for i in range(1, 4):
        previous_id = page.locator("#plot").get_attribute("data-shinywidgets-model-id")
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function(
            """previous => {
                const id = document.querySelector('#plot').dataset.shinywidgetsModelId;
                return id && id !== previous;
            }""",
            arg=previous_id,
        )
        page.wait_for_selector(ready_selector, timeout=30000)

    expect(page.locator("#plot > .lm-Widget")).to_have_count(1)
    expect(page.locator(ready_selector)).to_have_count(1)

    # Temporary models/comms return to the warmed-up baseline once the old
    # presentations' display leases are released and collected.
    if snapshot_id is not None and baseline is not None:
        expect(page.locator(f"#{snapshot_id}")).to_have_text(baseline)
    wait_for_browser_widget_counts(page, ["#plot"], browser_baseline)
    assert not errors, errors


def browser_widget_counts(page: Page, selectors: list[str]) -> dict[str, int]:
    return page.evaluate(BROWSER_WIDGET_COUNTS, arg=selectors)


def wait_for_browser_widget_counts(
    page: Page, selectors: list[str], expected: dict[str, int]
) -> None:
    page.wait_for_function(
        f"""({{selectors, expected}}) => {{
            const actual = ({BROWSER_WIDGET_COUNTS})(selectors);
            return Object.entries(expected).every(([key, value]) =>
                actual[key] === value
            );
        }}""",
        arg={"selectors": selectors, "expected": expected},
    )


BROWSER_WIDGET_COUNTS = """selectors => {
    const lifecycle = window.widgetLifecycle;
    const snapshot = lifecycle.snapshot();
    const mounts = selectors.map(selector =>
        lifecycle.mountSnapshot(document.querySelector(selector))
    );
    return {
        models: snapshot.models,
        waiters: snapshot.waiters,
        tasks: snapshot.tasks + mounts.reduce((n, m) => n + m.tasks, 0),
        mounts: mounts.reduce((n, m) => n + m.mounts, 0),
        views: mounts.reduce((n, m) => n + m.views, 0),
    };
}"""
