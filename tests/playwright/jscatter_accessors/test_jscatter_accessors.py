from __future__ import annotations

import numpy as np
from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def lasso_left_half(page: Page, canvas) -> None:
    # jupyter-scatter starts a lasso on a long press
    box = canvas.bounding_box()
    assert box is not None
    left, top = box["x"] + 5, box["y"] + 5
    mid, bottom = box["x"] + box["width"] / 2, box["y"] + box["height"] - 5
    page.mouse.move(left, top)
    page.mouse.down()
    page.wait_for_timeout(1200)
    for x, y in [(mid, top), (mid, bottom), (left, bottom), (left, top + 3)]:
        page.mouse.move(x, y, steps=10)
    page.mouse.up()


def click_point(page: Page, index: int) -> None:
    # Click-select one point, at its screen position (jupyter-scatter's own
    # pixel mapping, so this doesn't depend on the canvas's size)
    pos = page.evaluate(
        """(i) => {
          const canvas = document.querySelector('#sc canvas');
          const plot = canvas.parentElement.parentElement;
          const [px, py] = plot.api.getScreenPosition(i);
          const rect = canvas.getBoundingClientRect();
          return [rect.x + px, rect.y + py];
        }""",
        index,
    )
    page.mouse.click(*pos)


def test_selection_follows_lasso_and_click(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 800})
    page.goto(local_app.url)

    canvas = page.locator("#sc canvas").first
    expect(canvas).to_be_visible(timeout=30000)
    # A fresh Scatter reports an empty selection
    expect(page.locator("#sel")).to_have_text("", timeout=30000)
    page.wait_for_timeout(1000)

    # Lasso the left half of the plot
    lasso_left_half(page, canvas)

    expect(page.locator("#sel")).not_to_have_text("", timeout=30000)
    lassoed = page.locator("#sel").inner_text()
    assert len(lassoed.split(",")) > 1

    # Click-select point 42
    click_point(page, 42)
    expect(page.locator("#sel")).to_have_text("42", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_selected_rows_follows_lasso_and_click(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 800})
    page.goto(local_app.url)

    canvas = page.locator("#sc canvas").first
    expect(canvas).to_be_visible(timeout=30000)
    expect(page.locator("#rows")).to_have_text("0 rows: ", timeout=30000)
    page.wait_for_timeout(1000)

    # The lasso's rows come from the app's own data frame (the df default)
    lasso_left_half(page, canvas)
    expect(page.locator("#rows")).not_to_have_text("0 rows: ", timeout=30000)

    # Click-select point 42: exactly that row of the frame
    click_point(page, 42)
    x42 = np.random.default_rng(0).uniform(0, 1, 200)[42]  # the app's df
    expect(page.locator("#rows")).to_have_text(f"1 rows: {x42:.2f}", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)
