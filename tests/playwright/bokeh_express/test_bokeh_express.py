from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc


def test_express_preloads_and_reuses_bokeh(page: Page, local_app: ShinyAppProc) -> None:
    page.goto(local_app.url)

    expect(page.locator("#plot .bk-Figure")).to_have_count(1, timeout=30000)
    expect(page.locator("#table .tabulator-row")).to_have_count(3, timeout=30000)
    expect(page.locator("#scatter .bk-Figure")).to_have_count(1, timeout=30000)
    expect(page.locator('script[src$="/js/bokeh.min.js"]')).to_have_count(1)
