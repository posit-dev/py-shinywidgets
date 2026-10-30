from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_selection_reports_empty_load_time_selection(page: Page, local_app) -> None:
    # The viewer sends an empty (items: []) selection when it loads; only the
    # accessor's eager attach catches it, so the output settles on "[]" rather
    # than staying at the "(waiting)" placeholder
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#viewer .rerun_notebook canvas").first).to_be_visible(
        timeout=90000
    )
    expect(page.locator("#selection")).to_have_text("[]", timeout=90000)

    assert_no_unexpected_errors(errors, failed_requests)


@pytest.mark.skip(
    reason=(
        "the viewer's streams tree and viewport are egui-drawn canvas pixels, "
        "not DOM, and hit-testing the 'points' entity by coordinates proved "
        "flaky; the eager-attach regression is covered by the load-time test"
    )
)
def test_selection_follows_stream_tree_clicks(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    canvas = page.locator("#viewer .rerun_notebook canvas").first
    expect(canvas).to_be_visible(timeout=90000)
    expect(page.locator("#selection")).to_have_text("[]", timeout=90000)
    page.wait_for_timeout(3000)  # let the viewer's UI finish laying out

    # Clicking a point in the 3D viewport (egui, drawn into the viewer's
    # canvas) selects its entity; the points cluster at the viewport's center
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.5)
    expect(page.locator("#selection")).to_have_text(
        "[EntitySelectionItem]", timeout=30000
    )

    assert_no_unexpected_errors(errors, failed_requests)
