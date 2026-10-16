import pytest
from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc


@pytest.mark.parametrize("path", ["", "nested/"])
def test_prebuilt_extension_loads_local_assets_on_a_later_render(
    page: Page, local_app: ShinyAppProc, path: str
) -> None:
    errors: list[str] = []
    failed_assets: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "response",
        lambda response: (
            failed_assets.append(response.url)
            if "bokeh-ext-review_ext" in response.url and response.status >= 400
            else None
        ),
    )
    page.goto(local_app.url + path)
    expect(page.get_by_role("heading", name="Core Bokeh loaded")).to_be_visible()
    assert page.locator('script[src*="bokeh-ext-review_ext"]').count() == 0

    page.get_by_role("button", name="Show extension").click()
    expect(page.get_by_role("heading", name="Extension render 1")).to_be_visible()
    expect(page.locator('script[src$="/custom@1.min.js"]')).to_have_count(1)
    expect(page.locator('script[src$="/helper@1.js"]')).to_have_count(1)
    assert (
        page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--extension-assets-loaded').trim()"
        )
        == "1"
    )

    page.get_by_role("button", name="Show extension").click()
    expect(page.get_by_role("heading", name="Extension render 2")).to_be_visible()
    expect(page.locator('script[src$="/custom@1.min.js"]')).to_have_count(1)
    assert not failed_assets, failed_assets
    assert not errors, errors
