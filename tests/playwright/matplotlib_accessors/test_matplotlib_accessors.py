from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)

COORDS = re.compile(r"^-?\d+\.\d{2},-?\d+\.\d{2}$")
LIMITS = re.compile(r"^(-?\d+\.\d{2},){3}-?\d+\.\d{2}$")


def goto_drawn(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#plot canvas:visible").first).to_be_visible(timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#plot", timeout=30000)
    # The limits accessor is seeded at render; wait for its first value
    expect(page.locator("#limits")).to_have_text(LIMITS, timeout=30000)


def click_center(page: Page) -> None:
    box = page.locator("#plot canvas:visible").first.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def test_clicked_reports_data_coordinates(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_drawn(page, local_app)
    expect(page.locator("#clicked")).to_have_text("None")

    click_center(page)
    expect(page.locator("#clicked")).to_have_text(COORDS, timeout=10000)

    # A click in the figure margin (outside any axes) is not a click on data
    before = page.locator("#clicked").inner_text()
    box = page.locator("#plot canvas:visible").first.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + 3, box["y"] + 3)
    page.wait_for_timeout(1000)
    assert page.locator("#clicked").inner_text() == before

    assert_no_unexpected_errors(errors, failed_requests)


def test_clicked_skips_toolbar_drags_and_limits_follow(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_drawn(page, local_app)
    clicked_before = page.locator("#clicked").inner_text()
    limits_before = page.locator("#limits").inner_text()

    # Activate the toolbar's zoom-to-rect mode and drag a rectangle
    toolbar = page.locator("#plot .jupyter-matplotlib-toolbar")
    zoom = page.locator("#plot [title^='Zoom to rectangle']")
    expect(zoom).to_be_visible(timeout=10000)
    zoom.click()
    box = page.locator("#plot canvas:visible").first.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.6, steps=8)
    page.mouse.up()

    # The drag was a zoom, not a click; limits update (after the 250 ms debounce)
    page.wait_for_timeout(1000)
    assert page.locator("#clicked").inner_text() == clicked_before
    expect(page.locator("#limits")).not_to_have_text(limits_before, timeout=10000)
    expect(page.locator("#limits")).to_have_text(LIMITS, timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_picked_reports_point_index(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_drawn(page, local_app)
    expect(page.locator("#picked")).to_have_text("None")

    click_center(page)  # the horizontal line runs through the canvas center
    expect(page.locator("#picked")).to_have_text(re.compile(r"^\d+(,\d+)*$"), timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_rerender_does_not_stack_click_handlers(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_drawn(page, local_app)

    # Exactly one evaluation happens at load
    expect(page.locator("#click_count")).to_have_text("1", timeout=10000)
    page.click("#rerender")
    # The re-render's reset forces one more evaluation, which is also the read
    # that re-attaches the click handler to the new canvas; only then is it
    # safe to click
    expect(page.locator("#click_count")).to_have_text("2", timeout=10000)
    expect(page.locator("#clicked")).to_have_text("None", timeout=10000)
    expect(page.locator("#limits")).to_have_text(LIMITS, timeout=10000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#plot", timeout=30000)

    click_center(page)
    # One click increments the server-side evaluation count by exactly one
    # (a cached figure rendered twice must not stack handlers)
    expect(page.locator("#click_count")).to_have_text("3", timeout=10000)
    expect(page.locator("#clicked")).to_have_text(COORDS, timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)
