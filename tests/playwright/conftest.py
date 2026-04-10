from __future__ import annotations

import pytest
from playwright.sync_api import Page
from shiny.run import ShinyAppProc


@pytest.fixture
def rerender_page(page: Page, local_app: ShinyAppProc) -> Page:
    page.goto(local_app.url)
    page.wait_for_selector("#plot .js-plotly-plot", timeout=30000)
    return page
