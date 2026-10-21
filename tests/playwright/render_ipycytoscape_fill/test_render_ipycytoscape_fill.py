from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Sizes (rounded) of an output, its ipywidgets container, and the cytoscape
# canvas inside it, plus the content box of the output's parent card body
SIZES_JS = """(id) => {
  const out = document.getElementById(id);
  const size = (el) => {
    const b = el.getBoundingClientRect();
    return { width: Math.round(b.width), height: Math.round(b.height) };
  };
  const body = out.closest('.card-body');
  const content = (el) => {
    const cs = getComputedStyle(el);
    return {
      width: Math.round(el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)),
      height: Math.round(el.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom)),
    };
  };
  return {
    out: size(out),
    widget: size(out.firstElementChild),
    canvas: size(out.querySelector('canvas')),
    body: body ? content(body) : null,
  };
}"""


def sizes(page: Page, output_id: str) -> dict:
    expect(page.locator(f"#{output_id} canvas").first).to_be_visible(timeout=30000)
    return page.evaluate(SIZES_JS, output_id)


def test_cytoscape_fills_fixed_height_card(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 1200})
    page.goto(local_app.url)

    s = sizes(page, "filled")
    # The card body is the fill container; output, widget and canvas all match it
    # (and not the widget's 400px CSS default)
    assert s["body"] is not None and s["body"]["height"] > 400
    assert s["out"] == s["body"]
    assert s["widget"] == s["out"]
    assert s["canvas"] == s["out"]

    # ... and it tracks the container when the window resizes
    page.set_viewport_size({"width": 600, "height": 1200})
    page.wait_for_function(
        "(w) => document.querySelector('#filled canvas').getBoundingClientRect().width < w",
        arg=s["canvas"]["width"],
    )
    narrow = sizes(page, "filled")
    assert narrow["canvas"] == narrow["out"] == narrow["body"]
    assert narrow["out"]["width"] < s["out"]["width"]

    assert_no_unexpected_errors(errors, failed_requests)


def test_cytoscape_respects_explicit_output_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    s = sizes(page, "explicit_output_height")
    assert s["out"]["height"] == 250
    assert s["widget"]["height"] == 250
    assert s["canvas"]["height"] == 250

    assert_no_unexpected_errors(errors, failed_requests)


def test_cytoscape_respects_explicit_widget_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    s = sizes(page, "explicit_widget_height")
    assert s["out"]["height"] == 300
    assert s["widget"]["height"] == 300
    assert s["canvas"]["height"] == 300

    assert_no_unexpected_errors(errors, failed_requests)
