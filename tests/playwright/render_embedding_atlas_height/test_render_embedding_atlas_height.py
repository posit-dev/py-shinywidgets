from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

HEIGHT_JS = """(sel) => {
  const el = document.querySelector(sel + ' .embedding-atlas-widget-container');
  return el ? el.getBoundingClientRect().height : -1;
}"""


def test_embedding_atlas_respects_explicit_heights(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 1000})
    page.goto(local_app.url)

    for sel in ("#output_height", "#widget_height", "#default_height"):
        expect(page.locator(f"{sel} .embedding-atlas-widget-container")).to_be_visible(
            timeout=30000
        )

    # Neither output may fill the 1000px viewport: they keep the height given
    # to output_widget() / set on the widget's layout
    assert page.evaluate(HEIGHT_JS, "#output_height") == 320
    assert page.evaluate(HEIGHT_JS, "#widget_height") == 360
    # Without an explicit height in a non-fillable page, shinywidgets' default
    # 400px basis for filling outputs applies (not the explorer's built-in 650px)
    assert page.evaluate(HEIGHT_JS, "#default_height") == 400

    # Chromium's headless build has no WebGPU, so only the embedding view's
    # own "Could not get WebGPU ..." errors are expected
    assert_no_unexpected_errors(
        [e for e in errors if "WebGPU" not in e], failed_requests
    )
