from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)

# Canvases with their sizes, piercing shadow roots (bokeh 3 renders into
# shadow DOM, and panel's ECharts container appends inside one)
CANVAS_SIZES_JS = """(sel) => {
    const sizes = [];
    const walk = (root) => {
        for (const el of root.querySelectorAll('*')) {
            if (el.tagName === 'CANVAS') {
                const r = el.getBoundingClientRect();
                sizes.push([Math.round(r.width), Math.round(r.height)]);
            }
            if (el.shadowRoot) walk(el.shadowRoot);
        }
    };
    for (const root of document.querySelectorAll(sel)) walk(root);
    return sizes;
}"""


def test_echarts_pane_and_gauge_render(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    # The original bug: panel's ECharts frontend requested its GL sub-bundle
    # from a bokeh-server-style /static/extensions/... URL nothing mounted.
    # Watch for any such request failing again.
    static_extension_failures: list[str] = []
    page.on(
        "response",
        lambda res: static_extension_failures.append(f"{res.status} {res.url}")
        if res.status >= 400 and "static/extensions" in res.url
        else None,
    )
    page.goto(local_app.url)

    # Both ECharts-backed components draw a non-trivial canvas
    for output_id, min_w, min_h in (("chart", 400, 250), ("gauge", 250, 200)):
        expect(page.locator(f"#{output_id}")).to_be_visible(timeout=30000)
        page.wait_for_function(
            CANVAS_HAS_PIXELS_JS, arg=f"#{output_id}", timeout=30000
        )
        sizes = page.evaluate(CANVAS_SIZES_JS, f"#{output_id}")
        assert sizes, f"no canvas under #{output_id}"
        w, h = sizes[0]
        assert w >= min_w and h >= min_h, f"#{output_id} canvas is {w}x{h}"

    assert static_extension_failures == []
    assert_no_unexpected_errors(errors, failed_requests)
