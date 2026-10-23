from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
    wait_for_red_pixels,
)

# An ipyvolume figure view renders two stacked canvases (the WebGL scene and
# a 2D selection overlay) inside .ipyvolume-canvas-container
CANVAS_CONTAINER = ".ipyvolume-canvas-container"


def test_ipyvolume_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator(f"#plot {CANVAS_CONTAINER}")).to_have_count(1, timeout=30000)
    # Wait for the first frame before interacting: a click that lands while
    # the page's main thread is still busy with WebGL setup can sit in the
    # renderer's event queue for a long time
    wait_for_red_pixels(page, "#plot canvas")
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old_canvas = page.locator("#plot canvas").first.element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i), timeout=30000)
        page.wait_for_function("(el) => !el.isConnected", arg=old_canvas, timeout=30000)
        expect(page.locator(f"#plot {CANVAS_CONTAINER}")).to_have_count(
            1, timeout=30000
        )
        wait_for_red_pixels(page, "#plot canvas")

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)


def test_ipyvolume_rerender_closes_old_models(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator(f"#plot {CANVAS_CONTAINER}")).to_have_count(1, timeout=30000)
    wait_for_red_pixels(page, "#plot canvas")

    def n_figures() -> int:
        return sum(1 for m in client_models(page) if m["name"] == "FigureModel")

    assert n_figures() == 1
    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i), timeout=30000)
        expect(page.locator(f"#plot {CANVAS_CONTAINER}")).to_have_count(
            1, timeout=30000
        )
        wait_for_red_pixels(page, "#plot canvas")

    # Each re-render's old figure must be closed in the browser, so the model
    # count settles back to 1
    waited = 0
    while n_figures() != 1:
        assert waited < 30000, client_models(page)
        page.wait_for_timeout(250)
        waited += 250

    assert_no_unexpected_errors(errors, failed_requests)
