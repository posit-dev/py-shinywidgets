from __future__ import annotations

from playwright.sync_api import Page
from shiny.run import ShinyAppProc

SPINNER_VISIBLE_JS = """
(sel) => {
  const el = document.querySelector(sel);
  if (!el || !el.classList.contains("recalculating")) {
    return false;
  }
  const spinner = getComputedStyle(el, "::after");
  return (
    getComputedStyle(el).visibility !== "hidden" &&
    spinner.visibility !== "hidden" &&
    spinner.content !== "none" &&
    parseFloat(spinner.opacity) > 0.9
  );
}
"""

# Like SPINNER_VISIBLE_JS, but also requires the (stale) widget content to be
# hidden. The checks must happen in a single evaluation so they're guaranteed
# to land inside the recalculating window.
SPINNER_VISIBLE_CHILDREN_HIDDEN_JS = """
(sel) => {
  const el = document.querySelector(sel);
  if (!el || !el.classList.contains("recalculating")) {
    return false;
  }
  const spinner = getComputedStyle(el, "::after");
  const spinnerVisible =
    getComputedStyle(el).visibility !== "hidden" &&
    spinner.visibility !== "hidden" &&
    spinner.content !== "none" &&
    parseFloat(spinner.opacity) > 0.9;
  const kids = Array.from(el.children);
  const kidsHidden =
    kids.length > 0 &&
    kids.every((child) => getComputedStyle(child).visibility === "hidden");
  return spinnerVisible && kidsHidden;
}
"""


def test_busy_indicator_shows_on_initially_hidden_widget(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.goto(local_app.url)

    # The widget hasn't rendered yet (the reactive event hasn't fired), so the
    # output element is hidden (i.e., `renderValue(null)` was called)
    plot = page.locator("#plot")
    plot.wait_for(state="hidden", timeout=30000)

    # Trigger the (slow) recalculation
    page.click("#submit")

    # While recalculating, the busy indicator (spinner) should be visible, even
    # though the output element itself has inline `visibility: hidden`
    # https://github.com/posit-dev/py-shinywidgets/issues/213
    page.wait_for_function(SPINNER_VISIBLE_JS, arg="#plot", timeout=10000)

    # The widget should still render (and reveal) once the calculation finishes
    plot.locator(".js-plotly-plot").wait_for(timeout=30000)
    plot.wait_for(state="visible", timeout=30000)


def test_busy_indicator_shows_for_plain_ipywidget(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.goto(local_app.url)

    # Same scenario as the plotly test, but for a widget that doesn't take
    # plotly's hide-until-settle code path in `renderValue()`
    slider = page.locator("#slider")
    slider.wait_for(state="hidden", timeout=30000)

    page.click("#submit")
    page.wait_for_function(SPINNER_VISIBLE_JS, arg="#slider", timeout=10000)

    slider.locator(".lm-Widget").wait_for(timeout=30000)
    slider.wait_for(state="visible", timeout=30000)


def test_busy_indicator_hides_stale_content_while_recalculating(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.goto(local_app.url)
    plot = page.locator("#plot")
    plot.wait_for(state="attached", timeout=30000)

    # Render the widget
    page.click("#submit")
    plot.locator(".js-plotly-plot").wait_for(timeout=30000)
    plot.wait_for(state="visible", timeout=30000)

    # Recalculate. While recalculating, the previous widget content should be
    # hidden so only the spinner shows (mirroring Shiny's htmlwidgets behavior)
    page.click("#submit")
    page.wait_for_function(
        SPINNER_VISIBLE_CHILDREN_HIDDEN_JS, arg="#plot", timeout=10000
    )

    # The new widget should still render (and reveal) once finished
    plot.wait_for(state="visible", timeout=30000)
