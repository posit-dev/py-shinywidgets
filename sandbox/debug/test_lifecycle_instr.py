from __future__ import annotations

import time

from playwright.sync_api import Page, expect

CANVAS_CONTAINER = ".ipyvolume-canvas-container"


def test_ipyvolume_rerender_lifecycle(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator(f"#fill_plot {CANVAS_CONTAINER}")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        t0 = time.time()
        old_canvas = page.locator("#fill_plot canvas").first.element_handle()
        page.click("#rerender")
        print(f"iter {i}: clicked at {time.time()-t0:.2f}s")
        try:
            expect(page.locator("#render_count")).to_have_text(str(i), timeout=20000)
        except AssertionError:
            print(f"iter {i}: render_count FAILED at {time.time()-t0:.2f}s, value={page.locator('#render_count').inner_text()}")
            print("button enabled:", page.locator("#rerender").is_enabled())
            raise
        print(f"iter {i}: count ok at {time.time()-t0:.2f}s")
        page.wait_for_function("(el) => !el.isConnected", arg=old_canvas, timeout=30000)
        expect(page.locator(f"#fill_plot {CANVAS_CONTAINER}")).to_have_count(1, timeout=30000)
        print(f"iter {i}: canvas swapped at {time.time()-t0:.2f}s")
