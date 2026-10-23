from __future__ import annotations

from playwright.sync_api import Page, expect


def plot_box(page: Page, output_id: str) -> dict[str, float]:
    # Locators pierce BokehJS's shadow DOM; the first canvas spans the plot
    canvas = page.locator(f"#{output_id} canvas").first
    expect(canvas).to_be_visible(timeout=30000)
    box = canvas.bounding_box()
    assert box is not None
    return box


def output_box(page: Page, output_id: str) -> dict[str, float]:
    box = page.locator(f"#{output_id}").bounding_box()
    assert box is not None
    return box


def test_unsized_figure_fills_its_card(page: Page, local_app) -> None:
    page.goto(local_app.url)
    plot, out = plot_box(page, "stretched"), output_box(page, "stretched")
    assert plot["width"] >= out["width"] - 2
    assert plot["height"] >= out["height"] - 2


def test_user_sized_figure_keeps_its_size(page: Page, local_app) -> None:
    page.goto(local_app.url)
    plot = plot_box(page, "fixed")
    assert (round(plot["width"]), round(plot["height"])) == (250, 150)


def test_stretched_plots_fill_an_explicit_height_output(page: Page, local_app) -> None:
    page.goto(local_app.url)
    # Previously these collapsed to a ~27-55px sliver
    assert plot_box(page, "explicit_height")["height"] >= 240
    # HoloViews pads its plot by 10px
    assert plot_box(page, "hv_explicit_height")["height"] >= 220
