from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import expose_manager

# Artificially slows manager.create_view() (the step that builds the *new*
# view) so the window between "Shiny stopped showing the recalculating
# spinner" and "the new view is attached" is wide enough to assert on
# deterministically, regardless of machine speed.
SLOW_CREATE_VIEW_JS = """() => {
  const manager = window.widgetManager;
  const original = manager.create_view.bind(manager);
  manager.create_view = (...args) => (
    new Promise((resolve) => setTimeout(resolve, 300)).then(() => original(...args))
  );
}"""

TAG_JS = """() => {
  const el = document.querySelector('#out');
  const child = el.children[0];
  if (child) child.setAttribute('data-sw-tag', 'orig');
}"""

STATE_JS = """() => {
  const el = document.querySelector('#out');
  const child = el.children[0];
  return {
    recalculating: el.classList.contains('recalculating'),
    tag: child ? child.getAttribute('data-sw-tag') : null,
    visibility: child ? getComputedStyle(child).visibility : null,
  };
}"""


def test_stale_content_is_not_revealed_before_new_view_is_ready(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    page.wait_for_selector("#out .lm-Widget", timeout=30000)

    page.evaluate(SLOW_CREATE_VIEW_JS)
    page.evaluate(TAG_JS)

    page.select_option("#color", "green")

    # create_view() is delayed 300ms, so the new view cannot possibly be
    # attached yet -- the original (red) node is still in the DOM. Shiny has
    # already stopped recalculating well before this point (it does so
    # synchronously, before renderValue() even starts). If shinywidgets
    # doesn't keep the stale content hidden itself during this window, it
    # flashes back to full visibility here.
    page.wait_for_timeout(150)
    state = page.evaluate(STATE_JS)
    assert state["tag"] == "orig", (
        "test setup assumption violated: view swapped too early"
    )
    assert not state["recalculating"]
    assert state["visibility"] != "visible", (
        "stale (red) content became visible again before the new (green) "
        "view was attached -- this is the render flash"
    )

    # Sanity check: the new view does eventually show up correctly.
    out = page.locator("#out")
    expect(out.locator("#payload")).to_have_text("green", timeout=5000)
    expect(out).to_be_visible()
