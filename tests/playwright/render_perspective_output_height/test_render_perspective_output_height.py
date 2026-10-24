from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_perspective_respects_output_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)

    viewer = page.locator("#viewer perspective-viewer")
    expect(viewer).to_have_count(1, timeout=60000)
    expect(viewer.locator("td").first).to_be_visible(timeout=60000)

    container = page.locator("#viewer").bounding_box()
    rendered = viewer.bounding_box()
    assert container is not None and rendered is not None
    print("output height:", {"container": container, "viewer": rendered})
    assert abs(container["height"] - 260) <= 1

    assert 0 <= container["height"] - rendered["height"] <= 6

    assert_no_unexpected_errors(errors, failed_requests)
