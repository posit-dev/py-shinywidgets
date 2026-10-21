from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# Heights (in px) of a card's body content box, the output inside it, and the
# widget's pieces. The card body is the fill container, so its content box (i.e.,
# minus padding) is what the output should match.
BOXES_JS = """(id) => {
  const out = document.getElementById(id);
  const body = out.parentElement;
  const cs = getComputedStyle(body);
  const pad = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
  const h = (el) => el.getBoundingClientRect().height;
  const scrollBody = out.querySelector('.dt-scroll-body');
  return {
    container: h(body) - pad,
    output: h(out),
    widget: h(out.querySelector('.lm-Widget')),
    dtContainer: h(out.querySelector('.dt-container')),
    scrollBody: h(scrollBody),
    scrollOverflow: scrollBody.scrollHeight > scrollBody.clientHeight,
    footerBottom: out.querySelector('.dt-info').getBoundingClientRect().bottom,
    outputBottom: out.getBoundingClientRect().bottom,
  };
}"""


def test_itables_renders_table_without_errors(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#table .dt-scroll-body table.dataTable")).to_be_visible(
        timeout=30000
    )
    expect(page.locator("#table tbody tr").first).to_contain_text("a")
    # a data frame (rather than an ITable) is coerced
    expect(page.locator("#explicit .dt-scroll-body table.dataTable")).to_be_visible()
    expect(page.locator("#explicit tbody tr").first).to_contain_text("a")

    assert_no_unexpected_errors(errors, failed_requests)


def test_itables_leaves_shiny_jquery_as_global(page: Page, local_app) -> None:
    # itables' bundle assigns its own jQuery to window.$, which breaks code that
    # expects Shiny's jQuery (e.g., bslib's card resize handling reads
    # $(el).data("shinyOutputBinding"))
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#table tbody tr").first).to_be_visible(timeout=30000)
    page.wait_for_function("() => window.$ === window.jQuery")

    # Resizing the (fillable) card exercises bslib's use of the global `$`
    page.set_viewport_size({"width": 1000, "height": 600})
    page.wait_for_timeout(500)

    assert_no_unexpected_errors(errors, failed_requests)


def test_itables_fills_container_and_tracks_resizes(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#table tbody tr").first).to_be_visible(timeout=30000)

    tall = page.evaluate(BOXES_JS, "table")
    # 50vh of a 900px viewport, less the card body's padding
    assert tall["container"] > 300
    for part in ("output", "widget", "dtContainer"):
        assert abs(tall[part] - tall["container"]) <= 1, (part, tall)
    # The table's body scrolls (200 rows) instead of growing past the container,
    # and the footer stays inside it
    assert tall["scrollOverflow"], tall
    assert tall["scrollBody"] < tall["container"], tall
    assert tall["footerBottom"] <= tall["outputBottom"] + 1, tall

    page.set_viewport_size({"width": 1000, "height": 600})
    page.wait_for_function(
        """(prev) => {
          const out = document.getElementById('table');
          return out.getBoundingClientRect().height < prev - 100;
        }""",
        arg=tall["container"],
    )
    short = page.evaluate(BOXES_JS, "table")
    assert short["container"] < tall["container"]
    for part in ("output", "widget", "dtContainer"):
        assert abs(short[part] - short["container"]) <= 1, (part, short)
    assert short["footerBottom"] <= short["outputBottom"] + 1, short

    assert_no_unexpected_errors(errors, failed_requests)


def test_itables_respects_explicit_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#explicit tbody tr").first).to_be_visible(timeout=30000)

    boxes = page.evaluate(BOXES_JS, "explicit")
    assert boxes["output"] == 250, boxes
    assert abs(boxes["widget"] - 250) <= 1, boxes
    assert abs(boxes["dtContainer"] - 250) <= 1, boxes
    assert boxes["scrollOverflow"], boxes
    assert boxes["footerBottom"] <= boxes["outputBottom"] + 1, boxes

    assert_no_unexpected_errors(errors, failed_requests)


def test_itables_selected_rows_roundtrip_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#selected")).to_have_text("[]", timeout=30000)
    rows = page.locator("#table tbody tr")
    rows.nth(1).click()
    expect(page.locator("#selected")).to_have_text("[1]")
    rows.nth(3).click(modifiers=["ControlOrMeta"])
    expect(page.locator("#selected")).to_have_text("[1, 3]")

    assert_no_unexpected_errors(errors, failed_requests)


def test_itables_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#table .dt-scroll-body table.dataTable")).to_be_visible(
        timeout=30000
    )
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    expect(page.locator("#table .itables_anywidget")).to_have_count(1)
    expect(page.locator("#table .dt-scroll-body")).to_have_count(1)
    # One live model + view per itables output (anywidget models are named
    # AnyModel); nothing is left over from the three re-renders
    any_models = [m for m in client_models(page) if m["name"] == "AnyModel"]
    assert [m["views"] for m in any_models] == [1, 1], any_models

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
