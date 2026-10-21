from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

local_app_plain = create_app_fixture(Path(__file__).parent / "app_plain.py")


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


def test_global_dollar_still_honors_non_jquery_writes(page: Page, local_app) -> None:
    # The guard against itables replacing `$` must not freeze it for the page
    page.goto(local_app.url)
    expect(page.locator("#nested tbody tr").first).to_be_visible(timeout=30000)
    page.wait_for_function("() => window.$ === window.jQuery")

    assert page.evaluate("() => { window.$ = 42; return window.$; }") == 42
    page.evaluate("""() => {
        const s = document.createElement('script');
        s.text = 'var $ = "classic"; window.__dollar = $;';
        document.head.appendChild(s);
    }""")
    assert page.evaluate("() => window.__dollar") == "classic"


def test_jquery_no_conflict_still_releases_dollar(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#nested tbody tr").first).to_be_visible(timeout=30000)
    page.wait_for_function("() => window.$ === window.jQuery")

    released = page.evaluate("""() => {
        window.jQuery.noConflict();
        return typeof window.$ === 'undefined';
    }""")
    assert released


def test_app_without_itables_leaves_dollar_alone(page: Page, local_app_plain) -> None:
    page.goto(local_app_plain.url)
    expect(page.locator("#plain .lm-Widget")).to_be_visible(timeout=30000)
    descriptor = page.evaluate("""() => {
        const d = Object.getOwnPropertyDescriptor(window, '$');
        return { accessor: !!(d && (d.get || d.set)) };
    }""")
    assert descriptor == {"accessor": False}
