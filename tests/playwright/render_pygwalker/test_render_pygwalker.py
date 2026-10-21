from __future__ import annotations

import re

from playwright.sync_api import Page, Route, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# Hosts of the (non-essential) images in PyGWalker's "Enable AI Agent" banner
BANNER_ASSETS = re.compile(r"^https://(www\.runcell\.dev|imagedelivery\.net)/")

# Each output's rendered element (.lm-Widget, which carries the widget's layout)
# and the container it should fit, as bounding boxes
BOXES_JS = """(id) => {
  const box = (el) => {
    const r = el.getBoundingClientRect();
    return { width: r.width, height: r.height };
  };
  const out = document.querySelector('#' + id);
  const widget = out.querySelector(':scope > .lm-Widget');
  return {
    output: box(out),
    widget: box(widget),
    scrollHeight: widget.scrollHeight,
    clientHeight: widget.clientHeight,
    overflowY: getComputedStyle(widget).overflowY,
  };
}"""


# Serve the banner's remote images as empty so tests don't depend on them
# (PyGWalker also loads leaflet's CSS from unpkg, which has to come from the
# network since it's pinned with a subresource integrity hash).
def stub_banner_assets(page: Page) -> None:
    def fulfill_empty(route: Route) -> None:
        route.fulfill(status=200, body="")

    page.route(BANNER_ASSETS, fulfill_empty)


def goto_ready(page: Page, local_app) -> None:
    stub_banner_assets(page)
    page.set_viewport_size({"width": 1200, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#explorer").get_by_text("Field List")).to_be_visible(
        timeout=30000
    )


def test_pygwalker_renders_dataframe(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_ready(page, local_app)

    # The columns of the DataFrame make it to the field list
    field_list = page.locator("#explorer")
    expect(field_list.get_by_text("city", exact=True).first).to_be_visible()
    expect(field_list.get_by_text("population", exact=True).first).to_be_visible()

    assert_no_unexpected_errors(errors, failed_requests)


def test_pygwalker_fills_fixed_height_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_ready(page, local_app)

    card_body = page.locator("#fill_card > .card-body").bounding_box()
    boxes = page.evaluate(BOXES_JS, "explorer")
    assert card_body is not None

    # The card is 650px tall; its body minus padding is what the output gets
    assert abs(boxes["output"]["height"] - card_body["height"]) <= 40
    assert boxes["output"]["height"] > 500
    assert abs(boxes["widget"]["height"] - boxes["output"]["height"]) <= 1
    assert abs(boxes["widget"]["width"] - boxes["output"]["width"]) <= 1

    # PyGWalker's UI is taller than the container, so it must scroll
    assert boxes["overflowY"] == "auto"
    assert boxes["scrollHeight"] > boxes["clientHeight"]

    assert_no_unexpected_errors(errors, failed_requests)


def test_pygwalker_respects_explicit_heights(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_ready(page, local_app)

    # output_widget(height="480px")
    expect(page.locator("#explicit_height").get_by_text("Field List")).to_be_visible()
    boxes = page.evaluate(BOXES_JS, "explicit_height")
    assert boxes["output"]["height"] == 480
    assert boxes["widget"]["height"] == 480
    assert boxes["scrollHeight"] > boxes["clientHeight"]

    # widget.layout.height = "420px"
    expect(page.locator("#widget_height").get_by_text("Field List")).to_be_visible()
    boxes = page.evaluate(BOXES_JS, "widget_height")
    assert boxes["output"]["height"] == 420
    assert boxes["widget"]["height"] == 420
    assert boxes["scrollHeight"] > boxes["clientHeight"]

    assert_no_unexpected_errors(errors, failed_requests)


def test_pygwalker_fetches_data_from_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_ready(page, local_app)

    # PyGWalker runs in kernel-computation mode, so the data tab's rows are
    # requested from Python over the widget comm (browser -> Python -> browser)
    page.locator("#explorer").get_by_text("Data", exact=True).first.click()
    expect(page.locator("#request_count")).not_to_have_text("0", timeout=30000)
    expect(page.locator("#explorer").get_by_text("city-7", exact=True)).to_be_visible(
        timeout=30000
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_pygwalker_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    goto_ready(page, local_app)
    expect(page.locator("#render_count")).to_have_text("0")

    initial = client_models(page)
    assert [m["name"] for m in initial].count("AnyModel") == 3

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator("#explorer").get_by_text("Field List")).to_be_visible()

    # Re-rendering replaces the view; neither old views nor old models may
    # accumulate in the browser
    expect(page.locator("#explorer > .lm-Widget")).to_have_count(1)
    expect(page.locator("#explorer").get_by_text("Field List")).to_have_count(1)
    after = client_models(page)
    assert sorted(m["name"] for m in after) == sorted(m["name"] for m in initial)
    assert all(m["views"] == 1 for m in after), after

    assert not any("widget is not attached" in e.lower() for e in errors)
    assert not any("no comm channel" in e.lower() for e in errors)
    assert_no_unexpected_errors(errors, failed_requests)
