from __future__ import annotations

from typing import Any

from playwright.sync_api import Page, Route, expect
from shiny.run import ShinyAppProc


# Patches the served output.js so the page's OutputManager is reachable as
# window.widgetManager (same pattern as tests/playwright/widget_view_retention).
# `_models` and each model's `.views` exist in production, so no bundle change
# is needed.
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


_MODELS_JS = """async () => {
    const models = await Promise.all(
        Object.values(window.widgetManager._models).map((p) => p.catch(() => null))
    );
    return models.filter((m) => m).map((m) => ({
        name: m.get('_model_name'),
        views: Object.keys(m.views || {}).length,
    }));
}"""


def client_models(page: Page) -> list[dict[str, Any]]:
    """Per-model summary (class name + live view count) of the browser's widget registry."""
    return page.evaluate(_MODELS_JS)


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
