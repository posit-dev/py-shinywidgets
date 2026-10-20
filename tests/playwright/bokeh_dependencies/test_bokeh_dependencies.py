import pytest
from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc


@pytest.mark.parametrize("path", ["", "anonymous/", "explicit/"])
def test_bokeh_loads_once_for_decorated_and_raw_widgets(
    page: Page, local_app: ShinyAppProc, path: str
) -> None:
    page.goto(local_app.url + path)

    expect(page.locator("#plot .bk-Figure")).to_have_count(1, timeout=30000)
    expect(page.locator("#widget .bk-Figure")).to_have_count(1, timeout=30000)
    expect(page.locator('script[src$="/js/bokeh.min.js"]')).to_have_count(1)
