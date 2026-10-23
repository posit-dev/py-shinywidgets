from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# [width, height] boxes of an output, its parent's content box, and the
# Mosaic widget element inside it
BOXES_JS = """(sel) => {
  const out = document.querySelector(sel);
  const parent = out.parentElement;
  const cs = getComputedStyle(parent);
  const px = (v) => parseFloat(v);
  const o = out.getBoundingClientRect();
  const w = out.querySelector('.mosaic-widget').getBoundingClientRect();
  return {
    out: [o.width, o.height],
    container: [
      parent.clientWidth - px(cs.paddingLeft) - px(cs.paddingRight),
      parent.clientHeight - px(cs.paddingTop) - px(cs.paddingBottom),
    ],
    widget: [w.width, w.height],
  };
}"""


def wait_for_plots(page: Page, selector: str) -> None:
    expect(page.locator(f"{selector} .plot svg")).to_have_count(2, timeout=30000)


def test_mosaic_renders_linked_plots(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    wait_for_plots(page, "#mosaic")
    # 500 points drawn in the scatterplot, and the histogram's bars
    expect(page.locator("#mosaic .plot svg circle")).to_have_count(500)
    assert page.locator("#mosaic .plot svg rect").count() > 5
    expect(page.locator("#selected_rows")).to_have_text("500")

    assert_no_unexpected_errors(errors, failed_requests)


def test_mosaic_fills_fillable_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1100, "height": 800})
    page.goto(local_app.url)
    wait_for_plots(page, "#mosaic")

    boxes = page.evaluate(BOXES_JS, "#mosaic")
    assert abs(boxes["out"][0] - boxes["container"][0]) <= 1
    assert abs(boxes["out"][1] - boxes["container"][1]) <= 1
    assert abs(boxes["widget"][0] - boxes["out"][0]) <= 1
    assert abs(boxes["widget"][1] - boxes["out"][1]) <= 1
    assert boxes["out"][1] > 400

    # ... and tracks the container as it changes size
    page.evaluate(
        "document.querySelector('#mosaic').closest('.card').style.height = '350px'"
    )
    page.wait_for_function(
        "() => document.querySelector('#mosaic').getBoundingClientRect().height < 340"
    )
    resized = page.evaluate(BOXES_JS, "#mosaic")
    assert abs(resized["out"][1] - resized["container"][1]) <= 1
    assert abs(resized["widget"][1] - resized["out"][1]) <= 1

    assert_no_unexpected_errors(errors, failed_requests)


def test_mosaic_respects_explicit_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_plots(page, "#mosaic_fixed")

    boxes = page.evaluate(BOXES_JS, "#mosaic_fixed")
    assert abs(boxes["out"][1] - 260) <= 1

    assert_no_unexpected_errors(errors, failed_requests)


def test_mosaic_brush_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_plots(page, "#mosaic")

    # Initially nothing is brushed, so every row is selected
    expect(page.locator("#selected_rows")).to_have_text("500")

    # Brushing the scatterplot syncs the selection (the widget's `params`
    # trait) back to Python, where it filters the DuckDB table
    box = page.locator("#mosaic .plot svg").first.bounding_box()
    assert box is not None
    x0, y0 = box["x"] + box["width"] * 0.4, box["y"] + box["height"] * 0.3
    page.mouse.move(x0, y0)
    page.mouse.down()
    page.mouse.move(x0 + 80, y0 + 60, steps=8)
    page.mouse.up()

    expect(page.locator("#selected_rows")).not_to_have_text("500", timeout=30000)
    selected = int(page.locator("#selected_rows").inner_text())
    assert 0 < selected < 500

    assert_no_unexpected_errors(errors, failed_requests)


def test_mosaic_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    wait_for_plots(page, "#mosaic")
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        wait_for_plots(page, "#mosaic")

    # Re-rendering replaces the widget, but the old view must be disposed
    # (i.e., no accumulation of dashboards)
    expect(page.locator("#mosaic .mosaic-widget")).to_have_count(1)
    expect(page.locator("#mosaic .plot svg")).to_have_count(2)
    mosaic_views = [m["views"] for m in client_models(page) if m["name"] == "AnyModel"]
    # one view for each of the two outputs, none left over from retired renders
    assert sorted(mosaic_views) == [1, 1]

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
