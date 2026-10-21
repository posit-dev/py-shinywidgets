from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_explicit_scroll_y_is_respected_with_scroll_x(page: Page, local_app) -> None:
    # DataTables writes `width: 100%` inline on the scroll body when scrollX is set,
    # so the fill CSS must not key on inline styles it doesn't control
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    body = page.locator("#scrolly .dt-scroll-body")
    expect(body.locator("tbody tr").first).to_be_visible(timeout=30000)
    box = body.bounding_box()
    assert box is not None
    assert abs(box["height"] - 150) <= 1, box

    assert_no_unexpected_errors(errors, failed_requests)


def test_nested_itable_leaves_shiny_jquery_as_global(page: Page, local_app) -> None:
    # An ITable nested in another widget loads itables' bundle (which replaces the
    # global `$`) after the outer widget has rendered
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 900})
    page.goto(local_app.url)

    expect(page.locator("#nested tbody tr").first).to_be_visible(timeout=30000)
    page.wait_for_function("() => window.$ === window.jQuery")

    # Resizing the (fillable) card exercises bslib's use of the global `$`
    page.set_viewport_size({"width": 1000, "height": 600})
    page.wait_for_timeout(500)
    assert page.evaluate("() => window.$ === window.jQuery")

    assert_no_unexpected_errors(errors, failed_requests)
