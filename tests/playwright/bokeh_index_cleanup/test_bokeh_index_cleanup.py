from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc

# Root bokehjs views register themselves in the page-global Bokeh.index
# (a Proxy over a ViewManager whose ownKeys are the root views' model ids).
# jupyter_bokeh's BokehView never removes them, so without the shinywidgets
# patch every re-render adds entries that are never released.
BOKEH_INDEX_SIZE_JS = "() => Object.keys(window.Bokeh.index).length"


def test_bokeh_index_stays_bounded_on_rerender(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.goto(local_app.url)
    page.wait_for_selector("#plot .bk-Figure", timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    baseline = page.evaluate(BOKEH_INDEX_SIZE_JS)
    assert baseline > 0

    for i in range(1, 4):
        old_node = page.locator("#plot > .lm-Widget").element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        # The old view is removed (and its bokehjs views dropped from
        # Bokeh.index) before its replacement attaches
        page.wait_for_function("(node) => !node.isConnected", arg=old_node)

    # The replacement view's own index entries may land asynchronously, so
    # wait for the count to settle back to (at most) the baseline rather than
    # asserting a sample that could race view construction
    page.wait_for_function(
        f"(baseline) => Object.keys(window.Bokeh.index).length <= {baseline}",
        arg=baseline,
        timeout=10000,
    )
    assert page.evaluate(BOKEH_INDEX_SIZE_JS) <= baseline
