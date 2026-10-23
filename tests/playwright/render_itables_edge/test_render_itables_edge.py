from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

local_app_plain = create_app_fixture(Path(__file__).parent / "app_plain.py")
local_app_nonconfig_dollar = create_app_fixture(
    Path(__file__).parent / "app_nonconfig_dollar.py"
)
local_app_formatted = create_app_fixture(Path(__file__).parent / "app_formatted.py")
local_app_dark = create_app_fixture(Path(__file__).parent / "app_dark.py")


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


def test_non_jquery_dollar_survives_foreign_jquery_write(page: Page, local_app) -> None:
    # A non-jQuery `$` (e.g., left by jQuery.noConflict() or another library) is
    # kept by the guard; a later refused jQuery write must not clear it
    page.goto(local_app.url)
    expect(page.locator("#nested tbody tr").first).to_be_visible(timeout=30000)
    page.wait_for_function("() => window.$ === window.jQuery")

    page.evaluate("() => { window.$ = function customDollar() {}; }")
    page.evaluate("""() => {
        const foreign = function () {};
        foreign.fn = { jquery: '9.9.9-foreign' };
        window.$ = foreign;
    }""")
    assert page.evaluate("() => window.$.name") == "customDollar"


def test_dollar_can_be_restored_to_page_jquery(page: Page, local_app) -> None:
    # After noConflict() releases `$`, assigning the page jQuery back must restore
    # the binding that Shiny's global-`$` call sites use
    page.goto(local_app.url)
    expect(page.locator("#nested tbody tr").first).to_be_visible(timeout=30000)
    page.wait_for_function("() => window.$ === window.jQuery")

    released = page.evaluate("""() => {
        window.jQuery.noConflict();
        return typeof window.$ === 'undefined';
    }""")
    assert released

    page.evaluate("() => { window.$ = window.jQuery; }")
    assert page.evaluate("() => window.$ === window.jQuery")


def test_app_without_itables_leaves_dollar_alone(page: Page, local_app_plain) -> None:
    page.goto(local_app_plain.url)
    expect(page.locator("#plain .lm-Widget")).to_be_visible(timeout=30000)
    descriptor = page.evaluate("""() => {
        const d = Object.getOwnPropertyDescriptor(window, '$');
        return { accessor: !!(d && (d.get || d.set)) };
    }""")
    assert descriptor == {"accessor": False}


def test_nonconfigurable_dollar_binding_does_not_break_itable(
    page: Page, local_app_nonconfig_dollar
) -> None:
    # A classic script that ran `var $` before jQuery loaded leaves the global
    # binding non-configurable; the guard can't install its accessor there and
    # must fall back without aborting model initialization or losing the page jQuery
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_nonconfig_dollar.url)

    expect(page.locator("#table tbody tr").first).to_be_visible(timeout=30000)
    page.wait_for_function("() => window.$ === window.jQuery")

    # The binding stays a plain (writable, non-configurable) data property; no
    # accessor could be installed on it
    descriptor = page.evaluate("""() => {
        const d = Object.getOwnPropertyDescriptor(window, '$');
        return { writable: !!d.writable, accessor: !!(d.get || d.set) };
    }""")
    assert descriptor == {"writable": True, "accessor": False}

    # itables' bundle did replace `$` while its module evaluated, so the restore
    # path must have lent its DataTables plugin to the page jQuery
    assert page.evaluate("() => typeof window.jQuery.fn.dataTable !== 'undefined'")

    assert_no_unexpected_errors(errors, failed_requests)


def test_dollar_keeps_datatables_helpers_for_js_options(
    page: Page, local_app_formatted
) -> None:
    # itables evaluates JavascriptCode options against the global `$`, so the page
    # jQuery must expose the DataTables plugin that came with itables' own jQuery
    errors, failed_requests = collect_errors(page)
    page.goto(local_app_formatted.url)

    cells = page.locator("#formatted tbody tr td:nth-child(2)")
    expect(cells.first).to_have_text("$1,234.50", timeout=30000)
    expect(cells.nth(1)).to_have_text("$6.25")
    assert page.evaluate("() => window.$ === window.jQuery")
    assert (
        page.evaluate(
            "() => $('#formatted table.dataTable').DataTable().rows().count()"
        )
        == 2
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_table_follows_bootstrap_dark_mode(page: Page, local_app_dark) -> None:
    # itables doesn't recognize Bootstrap's `data-bs-theme`, so without help its
    # white background sits under the page's light dark-mode text
    page.goto(local_app_dark.url)
    expect(page.locator("#table tbody tr").first).to_be_visible(timeout=30000)
    page.wait_for_function(
        "() => document.documentElement.getAttribute('data-bs-theme') === 'dark'"
    )

    colors = page.evaluate("""() => {
        const style = getComputedStyle(document.querySelector('#table .dt-container'));
        return {
            background: style.backgroundColor,
            body: getComputedStyle(document.body).backgroundColor,
        };
    }""")
    assert colors["background"] == colors["body"], colors
