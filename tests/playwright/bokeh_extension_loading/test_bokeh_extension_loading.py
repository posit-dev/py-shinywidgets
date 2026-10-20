from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc


def test_panel_loads_assets_introduced_by_a_later_render(
    page: Page, local_app: ShinyAppProc
) -> None:
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(local_app.url)
    page.get_by_role("button", name="Show Markdown").click()
    expect(page.get_by_role("heading", name="Initial content")).to_be_visible()

    page.get_by_role("button", name="Show table", exact=True).click()

    expect(
        page.locator("#panel_output .tabulator-row [tabulator-field='x']")
    ).to_have_text(["1", "2", "3"], timeout=30000)
    assert not page_errors, page_errors
