from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc

SPINNER_VISIBLE_JS = """
() => {
  const el = document.querySelector("#plot");
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


def test_busy_indicator_shows_on_initially_hidden_widget(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.goto(local_app.url)

    # The widget hasn't rendered yet (the reactive event hasn't fired), so the
    # output element is hidden (i.e., `renderValue(null)` was called)
    plot = page.locator("#plot")
    expect(plot).to_be_hidden(timeout=30000)

    # Trigger the (slow) recalculation
    page.click("#submit")

    # While recalculating, the busy indicator (spinner) should be visible, even
    # though the output element itself has inline `visibility: hidden`
    # https://github.com/posit-dev/py-shinywidgets/issues/213
    page.wait_for_function(SPINNER_VISIBLE_JS, timeout=10000)

    # The widget should still render (and reveal) once the calculation finishes
    expect(page.locator("#plot .js-plotly-plot")).to_have_count(1, timeout=30000)
    expect(plot).to_be_visible(timeout=30000)
