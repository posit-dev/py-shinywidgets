from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)
from tests.playwright.render_embedding_atlas.app import docs

CONTAINER = "#atlas .embedding-atlas-widget-container"

# Bounding boxes of the output element, the rendered Embedding Atlas, and the
# card body that holds the output
BOXES_JS = """() => {
  const rect = (el) => {
    const r = el.getBoundingClientRect();
    return { width: r.width, height: r.height };
  };
  const contentBox = (el) => {
    const cs = getComputedStyle(el);
    return {
      width: el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
      height: el.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom),
    };
  };
  return {
    output: rect(document.querySelector('#atlas')),
    atlas: rect(document.querySelector('#atlas .embedding-atlas-widget-container')),
    body: contentBox(document.querySelector('.card-body')),
  };
}"""


def unexpected_errors(errors: list[str]) -> list[str]:
    # - Chromium's headless build has no WebGPU, so the embedding view itself
    #   (but not the rest of the explorer) logs "Could not get WebGPU ..."
    return [e for e in errors if "WebGPU" not in e]


def test_embedding_atlas_renders(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator(CONTAINER)).to_be_visible(timeout=30000)
    # The explorer's table is backed by DuckDB queries answered by Python
    # (via the widget's custom messages), so seeing the rows means the full
    # browser <-> Python data path works
    expect(page.locator("#atlas").get_by_text("item 0", exact=True)).to_be_visible(
        timeout=30000
    )
    expect(page.locator("#atlas").get_by_text("300 / 300 points")).to_be_visible()

    assert_no_unexpected_errors(unexpected_errors(errors), failed_requests)


def test_embedding_atlas_fills_fillable_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 700})
    page.goto(local_app.url)
    expect(page.locator(CONTAINER)).to_be_visible(timeout=30000)

    wide = page.evaluate(BOXES_JS)
    assert wide["atlas"]["width"] == wide["output"]["width"]
    assert wide["atlas"]["height"] == wide["output"]["height"]
    assert wide["output"]["height"] > 300
    # The output spans its card body's width and doesn't overflow its height
    # clientWidth/Height are rounded; the bounding boxes are fractional
    assert abs(wide["output"]["width"] - wide["body"]["width"]) <= 1
    assert wide["output"]["height"] <= wide["body"]["height"] + 1

    # ... and it tracks the container when the window shrinks
    page.set_viewport_size({"width": 700, "height": 520})
    page.wait_for_function(
        "(h) => document.querySelector('#atlas').getBoundingClientRect().height < h",
        arg=wide["output"]["height"],
    )
    narrow = page.evaluate(BOXES_JS)
    assert narrow["atlas"]["width"] == narrow["output"]["width"]
    assert narrow["atlas"]["height"] == narrow["output"]["height"]
    assert narrow["output"]["width"] < wide["output"]["width"]

    # ... and grows past the explorer's built-in 650px height when there's room
    page.set_viewport_size({"width": 900, "height": 1200})
    page.wait_for_function(
        "() => document.querySelector('#atlas').getBoundingClientRect().height > 650"
    )
    tall = page.evaluate(BOXES_JS)
    assert tall["atlas"]["height"] == tall["output"]["height"]
    assert tall["output"]["height"] <= tall["body"]["height"] + 1

    assert_no_unexpected_errors(unexpected_errors(errors), failed_requests)


def test_embedding_atlas_selection_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#selection_size")).to_have_text("300", timeout=30000)
    expect(page.locator("#atlas").get_by_text("item 0", exact=True)).to_be_visible(
        timeout=30000
    )

    # Clicking a bar in the "group" chart filters the data; the browser syncs
    # the resulting predicate to Python, where reactive_read() picks it up.
    # (Chart bar labels, unlike table cells, are `flex-none` elements.)
    bar_label = page.locator("#atlas div.flex-none", has_text=re.compile(r"^c$"))
    bar_label.click()
    expected = int((docs["group"] == "c").sum())
    assert 0 < expected < len(docs)
    expect(page.locator("#selection_size")).to_have_text(str(expected), timeout=30000)

    assert_no_unexpected_errors(unexpected_errors(errors), failed_requests)


def test_embedding_atlas_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator(CONTAINER)).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")
    expect(page.locator("#atlas").get_by_text("item 0", exact=True)).to_be_visible(
        timeout=30000
    )
    initial_views = page.evaluate("() => window.widgetManager._liveViews.size")
    initial_models = len(client_models(page))

    for i in range(1, 4):
        # Let the new explorer finish loading (not just the old one's rows being
        # visible) before the next re-render tears it down
        old_container = page.locator(CONTAINER).element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_container)
        expect(page.locator("#atlas").get_by_text("item 0", exact=True)).to_be_visible(
            timeout=30000
        )

    # Re-rendering replaces the widget, but the old view must be disposed
    expect(page.locator(CONTAINER)).to_have_count(1)
    assert page.evaluate("() => window.widgetManager._liveViews.size") == initial_views
    # Only the live widget (and its layout) keep a view; the models of earlier
    # renders are gone
    assert len(client_models(page)) == initial_models

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(unexpected_errors(errors), failed_requests)


# Send SQL the way the explorer does (a custom message on its model) and resolve
# with the Python side's reply. The reply is intercepted before it reaches the
# explorer's own listener, which throws on a request it didn't make.
BROWSER_SQL_JS = """async ([type, sql]) => {
  const models = await Promise.all(Object.values(window.widgetManager._models));
  const model = models.find(
    (m) => (m.get('_anywidget_id') || '').endsWith('EmbeddingAtlasWidget')
  );
  const uuid = 'browser-sql-probe';
  return await new Promise((resolve) => {
    const trigger = model.trigger;
    model.trigger = function (name, ...args) {
      if (name === 'msg:custom' && args[0].uuid === uuid) {
        model.trigger = trigger;
        resolve(args[0]);
        return this;
      }
      return trigger.apply(this, [name, ...args]);
    };
    model.send({ type, sql, uuid });
  });
}"""


def test_embedding_atlas_browser_sql_cannot_touch_server_files(
    page: Page, local_app, tmp_path
) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#atlas").get_by_text("item 0", exact=True)).to_be_visible(
        timeout=30000
    )

    # Any visitor can send the explorer's SQL messages; with the connection
    # locked down (the renderer's default), they can't write or read files
    target = tmp_path / "written-by-browser.csv"
    reply = page.evaluate(
        BROWSER_SQL_JS, ["exec", f"COPY (SELECT 1 AS x) TO '{target}'"]
    )
    assert "Permission Error" in reply.get("error", "")
    assert not target.exists()

    secret = tmp_path / "secret.csv"
    secret.write_text("x\nserver-only\n")
    reply = page.evaluate(BROWSER_SQL_JS, ["json", f"SELECT * FROM '{secret}'"])
    assert "Permission Error" in reply.get("error", "")

    # ... nor undo the lockdown
    reply = page.evaluate(BROWSER_SQL_JS, ["exec", "SET enable_external_access = true"])
    assert "error" in reply

    # The explorer's own queries keep working
    reply = page.evaluate(
        BROWSER_SQL_JS, ["json", "SELECT count(*) AS n FROM embedding_atlas"]
    )
    assert reply["result"] == [{"n": len(docs)}]
