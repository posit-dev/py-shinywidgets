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


# Content box of an element (its bounding box minus padding and border)
CONTENT_BOX_JS = """(sel) => {
  const el = document.querySelector(sel);
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const sum = (...props) => props.reduce((n, p) => n + parseFloat(cs[p]), 0);
  return {
    width: r.width - sum('paddingLeft', 'paddingRight', 'borderLeftWidth', 'borderRightWidth'),
    height: r.height - sum('paddingTop', 'paddingBottom', 'borderTopWidth', 'borderBottomWidth'),
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

    card_body = page.evaluate(CONTENT_BOX_JS, "#fill_card > .card-body")
    boxes = page.evaluate(BOXES_JS, "explorer")

    # The output fills the card body's content box exactly (card is 650px tall,
    # so this also rules out the output sitting at its content height)
    assert abs(boxes["output"]["height"] - card_body["height"]) <= 1
    assert abs(boxes["output"]["width"] - card_body["width"]) <= 1
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


# Send a request the way PyGWalker's UI does (a pyg_request message on the
# widget's model) and resolve with Python's reply. The reply is intercepted
# before it reaches PyGWalker's own listener, which didn't make the request.
PYG_REQUEST_JS = """async ([action, data]) => {
  const models = await Promise.all(Object.values(window.widgetManager._models));
  const model = models.find((m) => m.get('props'));
  const rid = 'pyg-request-probe-' + Math.random();
  return await new Promise((resolve) => {
    const trigger = model.trigger;
    model.trigger = function (name, ...args) {
      if (name === 'msg:custom' && args[0].type === 'pyg_response') {
        const msg = JSON.parse(args[0].data);
        if (msg.rid === rid) {
          model.trigger = trigger;
          resolve(msg.data);
          return this;
        }
      }
      return trigger.apply(this, [name, ...args]);
    };
    model.send({ type: 'pyg_request', msg: { action, rid, data } });
  });
}"""


def test_pygwalker_browser_sql_cannot_touch_server_files(
    page: Page, local_app, tmp_path
) -> None:
    page.route("**/output.js", expose_manager)
    goto_ready(page, local_app)

    def run_sql(sql: str) -> dict:
        return page.evaluate(PYG_REQUEST_JS, ["get_datas", {"sql": sql}])

    # Any visitor can send PyGWalker's SQL requests; with DuckDB locked down
    # (which render_pygwalker requires), they can't read or write server files
    secret = tmp_path / "secret.csv"
    secret.write_text("x\nserver-only\n")
    reply = run_sql(f"SELECT * FROM read_csv('{secret}')")
    assert reply["code"] != 0
    assert "server-only" not in str(reply)

    target = tmp_path / "written-by-browser.csv"
    run_sql(f"COPY (SELECT 1 AS x) TO '{target}'")
    assert not target.exists()

    # ... nor undo the lockdown
    assert run_sql("SET enable_external_access = true")["code"] != 0

    # PyGWalker's own queries keep working
    reply = run_sql('SELECT SUM("population") AS total FROM "pygwalker_mid_table"')
    assert reply["code"] == 0
    # (the app's populations are 1000 + 17 * i for i in range(30))
    assert reply["data"]["datas"] == [{"total": sum(1000 + 17 * i for i in range(30))}]


def test_pygwalker_rejects_unsafe_requests(page: Page, local_app) -> None:
    page.route("**/output.js", expose_manager)
    goto_ready(page, local_app)

    def send(action: str, data: dict) -> dict:
        return page.evaluate(PYG_REQUEST_JS, [action, data])

    # A visitor can send any request, but not set the server's Kanaries
    # credentials (pygwalker would save the token to its config file)
    reply = send("upload_spec_to_cloud", {"newToken": "visitor", "fileName": "x"})
    assert reply["code"] != 0
    assert "token" in reply["message"].lower()

    # ... nor make the server launch its gw:// protocol handler
    reply = send("open_in_desktop", {"spec": {}, "fields": {}})
    assert reply["code"] != 0
    assert "open_in_desktop" in reply["message"]
