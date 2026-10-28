from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def assert_fits_output(
    page: Page, output_id: str, chart_selector: str, height: float, aspect: float
) -> None:
    container = page.locator(f"#{output_id}").bounding_box()
    chart = page.locator(f"#{output_id} {chart_selector}").bounding_box()
    assert container is not None and chart is not None
    print(f"{output_id}:", {"container": container, "chart": chart})
    assert abs(container["height"] - height) <= 1
    # The chart must not be clipped by the output's overflow: hidden ...
    assert chart["y"] >= container["y"] - 1
    assert chart["y"] + chart["height"] <= container["y"] + container["height"] + 1
    # ... and its data-space aspect ratio must be preserved while fitting
    assert abs(chart["width"] / chart["height"] - aspect) < 0.05


def test_drawdata_respects_output_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    # Tall enough that the two fixed-height cards leave the filling card
    # real space in the page_fillable layout
    page.set_viewport_size({"width": 1400, "height": 2000})
    page.goto(local_app.url)

    # BarWidget's chart svg sits in a classless container (drawdata 0.5.x);
    # its buttons contain no svgs, so it's the only svg in the output
    scatter_chart = ".dd-scatter-svg-container svg"
    bars_chart = "svg"
    expect(page.locator(f"#scatter {scatter_chart}")).to_be_visible(timeout=60000)
    expect(page.locator(f"#bars {bars_chart}")).to_be_visible(timeout=60000)
    expect(page.locator(f"#fill_scatter {scatter_chart}")).to_be_visible(timeout=60000)

    # ScatterWidget's intrinsic space is 800x400, BarWidget's 800x550
    assert_fits_output(page, "scatter", scatter_chart, 500, aspect=2.0)
    assert_fits_output(page, "bars", bars_chart, 400, aspect=800 / 550)

    # The filling output's height is layout-driven, so just check the chart
    # fits inside it (with its aspect preserved)
    container = page.locator("#fill_scatter").bounding_box()
    chart = page.locator(f"#fill_scatter {scatter_chart}").bounding_box()
    assert container is not None and chart is not None
    print("fill_scatter:", {"container": container, "chart": chart})
    assert chart["y"] + chart["height"] <= container["y"] + container["height"] + 1
    assert abs(chart["width"] / chart["height"] - 2.0) < 0.05

    # Both are upstream drawdata frontend issues, not shinywidgets bugs:
    # - ScatterWidget sets an invalid `height="auto"` svg attribute
    #   (Chromium logs it in Jupyter too).
    # - BarWidget's render ends with `document.querySelector("button.control")
    #   .click()`, which throws because the view's element isn't attached to
    #   the document until after render (and would click the wrong widget's
    #   button if another BarWidget were attached). The throw aborts the last
    #   line of render, which just redraws the (empty) chart.
    assert_no_unexpected_errors(
        errors,
        failed_requests,
        allowed_errors=(
            "<svg> attribute height: Expected length",
            "Cannot read properties of null (reading 'click')",
        ),
    )
