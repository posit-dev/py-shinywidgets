from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    expose_manager,
)

# True once the ipympl canvas fills the output container's width and fits
# within its height (i.e., no overflow). ipympl draws the figure at a fixed
# pixel size by default; shinywidgets drives it to the container size.
CANVAS_FILLS_JS = """() => {
  const out = document.querySelector('#mpl');
  const canvas = out && out.querySelector('.jupyter-matplotlib-canvas-div canvas');
  if (!canvas) return false;
  const o = out.getBoundingClientRect();
  const c = canvas.getBoundingClientRect();
  return c.width >= 0.95 * o.width && c.height <= o.height && c.height >= 0.6 * o.height;
}"""

# Counts ResizeObservers that are observing (i.e., not yet disconnected)
COUNT_RESIZE_OBSERVERS_JS = """
(() => {
  const Native = window.ResizeObserver;
  window.liveResizeObservers = 0;
  window.ResizeObserver = class extends Native {
    observing = false;
    observe(...args) {
      if (!this.observing) window.liveResizeObservers++;
      this.observing = true;
      return super.observe(...args);
    }
    disconnect() {
      if (this.observing) window.liveResizeObservers--;
      this.observing = false;
      return super.disconnect();
    }
  };
})();
"""

LIVE_COUNTS_JS = """() => ({
  views: window.widgetManager._liveViews.size,
  observers: window.liveResizeObservers,
})"""

# True if the canvas (with its margins) ends above the footer, and the footer
# ends within the output: i.e., nothing at the bottom of the figure (the
# x-axis) is hidden behind the footer or clipped by the output.
FIGURE_FITS_JS = """() => {
  const out = document.querySelector('#mpl');
  const canvas = out.querySelector('.jupyter-matplotlib-canvas-div');
  const footer = out.querySelector('.jupyter-matplotlib-footer');
  const canvasBottom =
    canvas.getBoundingClientRect().bottom +
    parseFloat(getComputedStyle(canvas).marginBottom);
  const footerBox = footer.getBoundingClientRect();
  return (
    canvasBottom <= footerBox.top + 0.5 &&
    footerBox.bottom <= out.getBoundingClientRect().bottom + 0.5
  );
}"""

CANVAS_WIDTH_JS = """() => {
  const canvas = document.querySelector('#mpl .jupyter-matplotlib-canvas-div canvas');
  return canvas ? canvas.getBoundingClientRect().width : -1;
}"""


def test_matplotlib_fills_fillable_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(local_app.url)

    expect(page.locator("#mpl canvas").first).to_be_visible(timeout=30000)

    # The figure should grow from its natural size (640x480) to fill the card
    page.wait_for_function(CANVAS_FILLS_JS, timeout=30000)
    wide = page.evaluate(CANVAS_WIDTH_JS)

    # ... and it should track the container when the window resizes
    page.set_viewport_size({"width": 640, "height": 420})
    page.wait_for_function(CANVAS_FILLS_JS, timeout=30000)
    narrow = page.evaluate(CANVAS_WIDTH_JS)

    assert narrow < wide, (
        f"canvas width should shrink with the window ({wide} -> {narrow})"
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_matplotlib_rerender_releases_old_views(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.add_init_script(COUNT_RESIZE_OBSERVERS_JS)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#mpl canvas").first).to_be_visible(timeout=30000)
    page.wait_for_function(CANVAS_FILLS_JS, timeout=30000)
    initial = page.evaluate(LIVE_COUNTS_JS)

    for _ in range(3):
        old_canvas = page.locator("#mpl canvas").first.element_handle()
        page.click("#rerender")
        page.wait_for_function("(el) => !el.isConnected", arg=old_canvas)
        page.wait_for_function(CANVAS_FILLS_JS, timeout=30000)

    # ipympl's canvas view must be fully removed on rerender, else its fill
    # ResizeObserver stays connected and keeps resizing the retired model
    assert page.evaluate(LIVE_COUNTS_JS) == initial

    assert_no_unexpected_errors(errors, failed_requests)


def test_matplotlib_refits_when_footer_appears(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(local_app.url)

    expect(page.locator("#mpl canvas").first).to_be_visible(timeout=30000)
    page.wait_for_function(CANVAS_FILLS_JS, timeout=30000)
    page.wait_for_function(FIGURE_FITS_JS, timeout=5000)

    # ipympl's footer (the cursor readout) is empty until the pointer first
    # moves over the figure. Once it shows, the canvas must shrink to make room
    # for it rather than hide the bottom of the figure (the x-axis) behind it.
    page.locator("#mpl .jupyter-matplotlib-canvas-div canvas").last.hover()
    expect(page.locator("#mpl .jupyter-matplotlib-footer")).not_to_have_text("")
    page.wait_for_function(FIGURE_FITS_JS, timeout=5000)

    assert_no_unexpected_errors(errors, failed_requests)
