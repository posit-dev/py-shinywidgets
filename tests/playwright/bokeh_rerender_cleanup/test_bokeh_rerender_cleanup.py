from __future__ import annotations

from playwright.sync_api import Page
from tests.playwright.conftest import assert_rerender_cleanup


def test_bokeh_rerender_does_not_log_cleanup_errors(page: Page, local_app) -> None:
    assert_rerender_cleanup(
        page,
        local_app,
        snapshot_id="widget_snapshot",
        ready_selector="#plot .bk-Figure",
    )
