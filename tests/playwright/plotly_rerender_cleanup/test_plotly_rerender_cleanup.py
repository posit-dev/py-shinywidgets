from __future__ import annotations

from playwright.sync_api import Page
from tests.playwright.conftest import assert_rerender_cleanup


def test_plotly_rerender_does_not_log_cleanup_errors(page: Page, local_app) -> None:
    assert_rerender_cleanup(page, local_app, "#plot .js-plotly-plot")
