from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import expose_manager

# Holds manager.create_view() (the step that builds the *new* view) behind a
# test-controlled gate, so the window between "Shiny stopped showing the
# recalculating spinner" and "the new view is attached" stays open exactly
# until the test has inspected the stale content -- no fixed sleeps.
GATE_CREATE_VIEW_JS = """() => {
  const manager = window.widgetManager;
  const original = manager.create_view.bind(manager);
  window.__createViewEntered = false;
  const gate = new Promise((resolve) => {
    window.__releaseCreateView = resolve;
  });
  manager.create_view = (...args) => {
    window.__createViewEntered = true;
    return gate.then(() => original(...args));
  };
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

    page.evaluate(GATE_CREATE_VIEW_JS)
    page.evaluate(TAG_JS)

    page.select_option("#color", "green")

    # Wait until the server has responded and renderValue() is blocked inside
    # the gated create_view(): the new view cannot possibly be attached yet,
    # so the original (red) node is still in the DOM. Shiny has already
    # stopped recalculating before this point (it does so synchronously,
    # before renderValue() even starts). If shinywidgets doesn't keep the
    # stale content hidden itself during this window, it flashes back to
    # full visibility here.
    page.wait_for_function("() => window.__createViewEntered === true")
    state = page.evaluate(STATE_JS)
    assert state["tag"] == "orig", (
        "test setup assumption violated: view swapped too early"
    )
    assert not state["recalculating"]
    assert state["visibility"] != "visible", (
        "stale (red) content became visible again before the new (green) "
        "view was attached -- this is the render flash"
    )

    # Let view construction proceed; the new view shows up correctly.
    page.evaluate("() => window.__releaseCreateView()")
    out = page.locator("#out")
    expect(out.locator("#payload")).to_have_text("green", timeout=5000)
    expect(out).to_be_visible()


# Records, across the next re-render of an output, how long its inline
# visibility stays 'hidden'. Attribute mutations are observed reliably
# regardless of how brief the hidden window is, unlike polling.
def hidden_duration_js(output_id: str) -> str:
    return f"""() => {{
  const el = document.querySelector('#{output_id}');
  window.__hiddenDuration = new Promise((resolve) => {{
    let hiddenAt = null;
    const mo = new MutationObserver(() => {{
      if (el.style.visibility === 'hidden') {{
        hiddenAt = performance.now();
      }} else if (hiddenAt !== null) {{
        mo.disconnect();
        resolve(performance.now() - hiddenAt);
      }}
    }});
    mo.observe(el, {{attributes: true, attributeFilter: ['style']}});
  }});
}}"""


def test_text_only_widget_reveals_without_waiting_for_fallback(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.goto(local_app.url)
    page.wait_for_selector("#text_out .widget-html-content", timeout=30000)

    page.evaluate(hidden_duration_js("text_out"))
    page.select_option("#color", "green")
    hidden_ms = page.evaluate("() => window.__hiddenDuration")

    # A widget whose content is a bare text node (no element children) must
    # still count as a rendered implementation; otherwise reveal waits for
    # the 1s fallback on every render.
    assert hidden_ms < 500, (
        f"text-only widget stayed hidden for {hidden_ms:.0f}ms -- "
        "the implementation check didn't recognize it and reveal fell back "
        "to the 1s timeout"
    )
    expect(page.locator("#text_out")).to_be_visible()


@pytest.mark.parametrize(
    ("output_id", "ready_selector"),
    [
        # The view's root IS a <button> holding its description as text
        ("button_out", ".widget-button"),
        # The view's root is an <img>: neither children nor text
        ("image_out", "img.widget-image"),
    ],
)
def test_root_leaf_widget_reveals_without_waiting_for_fallback(
    page: Page, local_app: ShinyAppProc, output_id: str, ready_selector: str
) -> None:
    page.goto(local_app.url)
    page.wait_for_selector(f"#{output_id} {ready_selector}", timeout=30000)

    page.evaluate(hidden_duration_js(output_id))
    page.select_option("#color", "green")
    hidden_ms = page.evaluate("() => window.__hiddenDuration")

    # A widget whose root element is itself the rendered implementation
    # (no widget children below it) must count as rendered; otherwise
    # reveal waits for the 1s fallback on every render.
    assert hidden_ms < 500, (
        f"#{output_id} stayed hidden for {hidden_ms:.0f}ms -- "
        "the implementation check didn't recognize the renderable root and "
        "reveal fell back to the 1s timeout"
    )
    expect(page.locator(f"#{output_id}")).to_be_visible()


# Patches display_view() so the next render of #text_out attaches with its
# content emptied, then restores the text 300 ms later -- simulating a
# widget whose container attaches before its content arrives. Revealing
# must follow that subtree mutation, not the 1s fallback.
DELAY_CONTENT_JS = """() => {
  const target = document.querySelector('#text_out');
  const manager = window.widgetManager;
  const original = manager.display_view.bind(manager);
  manager.display_view = async (view, el) => {
    const result = await original(view, el);
    if (el === target) {
      manager.display_view = original;
      const content = el.querySelector('.widget-html-content');
      const text = content.textContent;
      content.textContent = '';
      setTimeout(() => { content.textContent = text; }, 300);
    }
    return result;
  };
}"""


def test_content_added_inside_attached_container_reveals_without_fallback(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    page.wait_for_selector("#text_out .widget-html-content", timeout=30000)

    page.evaluate(DELAY_CONTENT_JS)
    page.evaluate(hidden_duration_js("text_out"))
    page.select_option("#color", "green")
    hidden_ms = page.evaluate("() => window.__hiddenDuration")

    # The content re-appears 300 ms after attach; an observer that only
    # watched lmWidget's direct children would miss it and reveal would
    # wait for the 1s fallback.
    assert hidden_ms < 800, (
        f"output stayed hidden for {hidden_ms:.0f}ms -- "
        "content added inside an already-attached container didn't trigger "
        "the reveal, so it fell back to the 1s timeout"
    )
    expect(page.locator("#text_out")).to_be_visible()
