from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    wait_for_red_pixels,
)


def test_camera_follows_orbit(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    wait_for_red_pixels(page, "#plot canvas")
    # Seeded with the Python-side camera's position
    expect(page.locator("#camera")).to_have_text(
        re.compile(r"^-?\d+\.\d{3}(,-?\d+\.\d{3}){2}$"), timeout=30000
    )
    before = page.locator("#camera").inner_text()

    # Orbit-drag the canvas: the camera's position syncs back at orbit end
    box = page.locator("#plot canvas").first.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] / 2 + 100, box["y"] + box["height"] / 2 + 50, steps=10
    )
    page.mouse.up()
    expect(page.locator("#camera")).not_to_have_text(before, timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)
