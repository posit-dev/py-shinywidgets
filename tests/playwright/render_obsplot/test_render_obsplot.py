from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# [width, height] boxes of an output and of the chart SVG inside it
BOXES_JS = """(id) => {
  const out = document.getElementById(id);
  const svg = out.querySelector('.pyobsplot-plot svg[class^="plot-"]');
  const o = out.getBoundingClientRect();
  const s = svg.getBoundingClientRect();
  return {out: [o.width, o.height], svg: [s.width, s.height]};
}"""


# The chart figure's SVG has a `plot-*` class; Plot legends are additional,
# class-less SVGs
FIGURE_SVG = '.pyobsplot-plot svg[class^="plot-"]'


def wait_for_chart(page: Page, output_id: str, n_dots: int = 300) -> None:
    expect(page.locator(f"#{output_id} {FIGURE_SVG}")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator(f"#{output_id} {FIGURE_SVG} circle")).to_have_count(
        n_dots, timeout=30000
    )


def test_obsplot_renders_chart(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    wait_for_chart(page, "scatter")
    # The color legend is separate SVGs beside the figure's
    expect(page.locator("#scatter .pyobsplot-plot svg:not([class])")).to_have_count(2)

    assert_no_unexpected_errors(errors, failed_requests)


def test_obsplot_shows_tip_on_hover(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_chart(page, "scatter")

    dot = page.locator(f"#scatter {FIGURE_SVG} circle").first
    dot.hover(force=True)
    expect(page.locator(f"#scatter {FIGURE_SVG} [aria-label=tip]")).to_have_count(
        1, timeout=10000
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_obsplot_scales_svg_to_container(page: Page, local_app) -> None:
    # Observable Plot SVGs have a fixed pixel size (640px wide by default) and
    # shrink (aspect preserved) to fit a narrower container, but never grow
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 700, "height": 900})
    page.goto(local_app.url)
    wait_for_chart(page, "scatter")

    boxes = page.evaluate(BOXES_JS, "scatter")
    print(f"narrow: {boxes}")
    assert boxes["svg"][0] <= 640
    assert abs(boxes["svg"][0] - boxes["out"][0]) <= 2

    page.set_viewport_size({"width": 1600, "height": 900})
    page.wait_for_function(
        f"() => ({BOXES_JS})('scatter').out[0] > 900", timeout=10000
    )
    boxes = page.evaluate(BOXES_JS, "scatter")
    print(f"wide: {boxes}")
    assert boxes["svg"][0] == 640

    assert_no_unexpected_errors(errors, failed_requests)


def test_obsplot_respects_explicit_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_chart(page, "fixed")

    boxes = page.evaluate(BOXES_JS, "fixed")
    assert abs(boxes["out"][1] - 300) <= 1

    assert_no_unexpected_errors(errors, failed_requests)


def test_obsplot_spec_update_in_place(page: Page, local_app) -> None:
    # Assigning .widget.spec replaces the chart without re-rendering
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_chart(page, "scatter")
    expect(page.locator("#render_count")).to_have_text("0")

    page.click("#recolor")
    # The legend is gone in the new spec (and dots remain)
    expect(page.locator("#scatter .pyobsplot-plot svg:not([class])")).to_have_count(
        0, timeout=10000
    )
    expect(page.locator(f"#scatter {FIGURE_SVG} circle")).to_have_count(300)
    expect(page.locator("#render_count")).to_have_text("0")

    assert_no_unexpected_errors(errors, failed_requests)


def test_obsplot_rerender_releases_old_views(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    wait_for_chart(page, "scatter")
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old_svg = page.locator(f"#scatter {FIGURE_SVG}").element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_svg)
        wait_for_chart(page, "scatter")

    expect(page.locator("#scatter .pyobsplot-plot")).to_have_count(1)
    # One ObsplotWidget model per output, each with exactly one view
    widgets = [m for m in client_models(page) if m["name"] == "AnyModel"]
    assert [m["views"] for m in widgets] == [1, 1], widgets

    assert_no_unexpected_errors(errors, failed_requests)
