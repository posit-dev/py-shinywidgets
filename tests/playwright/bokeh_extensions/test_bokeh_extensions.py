from __future__ import annotations

from playwright.sync_api import Page, Route, expect
from shiny.run import ShinyAppProc


def test_panel_tabulator_is_styled_without_panel_cdn(
    page: Page, local_app: ShinyAppProc
) -> None:
    requests: list[str] = []

    def block_panel_cdn(route: Route) -> None:
        requests.append(route.request.url)
        route.abort()

    page.route("https://cdn.holoviz.org/**", block_panel_cdn)
    page.goto(local_app.url)

    expect(page.locator("#tabulator .tabulator-row")).to_have_count(3, timeout=30000)
    column = page.locator("#tabulator .tabulator-col[tabulator-field='int']")
    expect(column).to_have_css("display", "inline-flex", timeout=30000)
    assert not requests, requests


def test_panel_tabulator_renders(page: Page, local_app: ShinyAppProc) -> None:
    page_errors: list[str] = []
    page.on("pageerror", lambda err: page_errors.append(str(err)))

    page.goto(local_app.url)
    page.wait_for_selector("#tabulator .tabulator", timeout=30000)
    expect(page.locator("#tabulator .tabulator-row")).to_have_count(3)
    expect(
        page.locator("#tabulator .tabulator-row [tabulator-field='int']")
    ).to_have_text(["1", "2", "3"])
    expect(
        page.locator("#tabulator .tabulator-row [tabulator-field='str']")
    ).to_have_text(["A", "B", "C"])
    assert not page_errors, page_errors


def test_panel_perspective_loads_module_exports(
    page: Page, local_app: ShinyAppProc
) -> None:
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(local_app.url)
    viewer = page.locator("#perspective perspective-viewer")
    expect(viewer).to_be_visible(timeout=30000)
    page.wait_for_function("() => typeof window.perspective_viewer !== 'undefined'")
    rows = viewer.evaluate(
        """async (viewer) => {
            const table = await viewer.getTable();
            const view = await table.view();
            try {
                return await view.to_json();
            } finally {
                await view.delete();
            }
        }"""
    )
    assert [(row["x"], row["y"]) for row in rows] == [
        (1, 1),
        (2, 4),
        (3, 9),
        (4, 16),
    ]
    assert not page_errors, page_errors


def test_hvplot_renders(page: Page, local_app: ShinyAppProc) -> None:
    page_errors: list[str] = []
    page.on("pageerror", lambda err: page_errors.append(str(err)))

    page.goto(local_app.url)
    page.wait_for_selector("#hvplot .bk-Figure", timeout=30000)
    expect(page.locator("#hvplot .bk-Figure")).to_have_count(1)
    assert not page_errors, page_errors


def test_panel_tabulator_sorts_rows(page: Page, local_app: ShinyAppProc) -> None:
    page.goto(local_app.url)
    column = page.locator("#tabulator .tabulator-col[tabulator-field='int']")
    expect(column).to_be_visible(timeout=30000)

    column.click()
    column.click()

    expect(
        page.locator("#tabulator .tabulator-row [tabulator-field='int']")
    ).to_have_text(["3", "2", "1"])
    expect(
        page.locator("#tabulator .tabulator-row [tabulator-field='str']")
    ).to_have_text(["C", "B", "A"])


def test_panel_tabulator_rerender_replaces_contents(
    page: Page, local_app: ShinyAppProc
) -> None:
    page_errors: list[str] = []
    page.on("pageerror", lambda err: page_errors.append(str(err)))
    page.goto(local_app.url)
    expect(
        page.locator("#tabulator .tabulator-row [tabulator-field='int']")
    ).to_have_text(["1", "2", "3"], timeout=30000)

    page.get_by_role("button", name="Rerender table").click()

    expect(
        page.locator("#tabulator .tabulator-row [tabulator-field='int']")
    ).to_have_text(["2", "3", "4"])
    expect(page.locator("#tabulator .tabulator")).to_have_count(1)
    expect(page.locator("#tabulator > .lm-Widget")).to_have_count(1)
    assert not page_errors, page_errors
