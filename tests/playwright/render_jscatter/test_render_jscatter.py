from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# jupyter-scatter's plot container: the canvas sits in a wrapper inside it.
# Returns the container's height next to the output's, and the canvas's.
HEIGHTS_JS = """(id) => {
  const out = document.querySelector('#' + id);
  const canvas = out.querySelector('canvas');
  const plot = canvas.parentElement.parentElement;
  return {
    output: out.getBoundingClientRect().height,
    plot: plot.getBoundingClientRect().height,
    canvas: canvas.getBoundingClientRect().height,
  };
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


def wait_until_plot_fills_output(page: Page, id: str) -> None:
    page.wait_for_function(
        """(id) => {
          const out = document.querySelector('#' + id);
          const canvas = out && out.querySelector('canvas');
          if (!canvas) return false;
          const plot = canvas.parentElement.parentElement;
          return Math.abs(plot.getBoundingClientRect().height - out.clientHeight) <= 1;
        }""",
        arg=id,
        timeout=30000,
    )


def test_jscatter_renders_without_errors(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    canvas = page.locator("#fill_scatter canvas").first
    expect(canvas).to_be_visible(timeout=30000)
    box = canvas.bounding_box()
    assert box is not None and box["width"] > 0 and box["height"] > 0

    assert_no_unexpected_errors(errors, failed_requests)


def test_jscatter_fills_fillable_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 1000})
    page.goto(local_app.url)
    expect(page.locator("#fill_scatter canvas").first).to_be_visible(timeout=30000)
    wait_until_plot_fills_output(page, "fill_scatter")

    # jupyter-scatter draws at 240px unless told otherwise; filling means the
    # plot container now matches the (taller) output container
    heights = page.evaluate(HEIGHTS_JS, "fill_scatter")
    output_height = page.evaluate(
        "document.querySelector('#fill_scatter').clientHeight"
    )
    assert output_height > 300
    assert abs(heights["plot"] - output_height) <= 1
    assert heights["canvas"] > 240

    # ... and it tracks its container when the window shrinks
    page.set_viewport_size({"width": 1000, "height": 700})
    page.wait_for_function(
        """(before) => {
          const out = document.querySelector('#fill_scatter');
          const plot = out.querySelector('canvas').parentElement.parentElement;
          return out.clientHeight < before - 100 && Math.abs(plot.getBoundingClientRect().height - out.clientHeight) <= 1;
        }""",
        arg=output_height,
        timeout=30000,
    )
    shrunk = page.evaluate(HEIGHTS_JS, "fill_scatter")
    assert abs(shrunk["plot"] - shrunk["output"]) <= 1
    assert shrunk["canvas"] < heights["canvas"] - 100

    assert_no_unexpected_errors(errors, failed_requests)


def test_jscatter_explicit_height_is_respected(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 1000})
    page.goto(local_app.url)
    expect(page.locator("#fixed_scatter canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#fill_scatter canvas").first).to_be_visible(timeout=30000)
    wait_until_plot_fills_output(page, "fill_scatter")

    heights = page.evaluate(HEIGHTS_JS, "fixed_scatter")
    # The output still fills its card, but the plot keeps its own height (180px
    # plus 20px of axes padding)
    assert heights["canvas"] == 180
    assert heights["plot"] == 200
    assert heights["output"] > 300

    assert_no_unexpected_errors(errors, failed_requests)


def test_jscatter_selection_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 1000})
    page.goto(local_app.url)

    expect(page.locator("#selected")).to_have_text("0", timeout=30000)
    canvas = page.locator("#fill_scatter canvas").first
    expect(canvas).to_be_visible(timeout=30000)
    wait_until_plot_fills_output(page, "fill_scatter")

    # Lasso a region covering the plot area (jupyter-scatter starts a lasso on
    # a long press)
    box = canvas.bounding_box()
    assert box is not None
    left, top = box["x"] + 10, box["y"] + 10
    right, bottom = box["x"] + box["width"] - 10, box["y"] + box["height"] - 10
    page.mouse.move(left, top)
    page.mouse.down()
    page.wait_for_timeout(1200)
    for x, y in [(right, top), (right, bottom), (left, bottom), (left, top + 3)]:
        page.mouse.move(x, y, steps=10)
    page.mouse.up()

    # The browser's selection (a numpy-serialized buffer) reaches Python, and
    # reactive_read() turns it into a reactive value
    browser_count = page.evaluate(
        """() => {
          const plot = document.querySelector('#fill_scatter canvas').parentElement.parentElement;
          return plot.api.get('selectedPoints').length;
        }"""
    )
    assert browser_count > 1
    expect(page.locator("#selected")).to_have_text(str(browser_count), timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_jscatter_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.add_init_script(COUNT_RESIZE_OBSERVERS_JS)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#fill_scatter canvas").first).to_be_visible(timeout=30000)
    wait_until_plot_fills_output(page, "fill_scatter")
    expect(page.locator("#render_count")).to_have_text("0")

    def live_views() -> int:
        return sum(
            m["views"]
            for m in client_models(page)
            if m["name"] == "AnyModel"  # anywidget's model class
        )

    initial_canvases = page.locator("#fill_scatter canvas").count()
    initial_views = live_views()
    initial_observers = page.evaluate("window.liveResizeObservers")
    assert initial_views == 2  # the fill and fixed outputs

    for i in range(1, 4):
        old_canvas = page.locator("#fill_scatter canvas").first.element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_canvas)
        expect(page.locator("#fill_scatter canvas").first).to_be_visible(timeout=30000)
        wait_until_plot_fills_output(page, "fill_scatter")

    # Re-rendering replaces the widget, and the retired views (and their
    # fill ResizeObservers) must be released rather than accumulate
    expect(page.locator("#fill_scatter canvas")).to_have_count(initial_canvases)
    assert live_views() == initial_views
    assert page.evaluate("window.liveResizeObservers") == initial_observers

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
