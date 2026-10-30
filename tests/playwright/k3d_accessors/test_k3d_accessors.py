from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    wait_for_red_pixels,
)


def test_camera_waits_for_auto_fit_then_follows_orbit(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # Not-ready sentinel, end to end: camera() cancels (like req(False)) until
    # the browser's auto-fit reports the camera, so the output starts empty
    expect(page.locator("#camera")).to_have_text("", timeout=10000)

    wait_for_red_pixels(page, "#plot canvas")
    # Auto-fit reports a 9-element camera (position, target, up)
    expect(page.locator("#camera")).to_have_text(
        re.compile(r"^-?\d+\.\d{3}(,-?\d+\.\d{3}){8}$"), timeout=30000
    )
    before = page.locator("#camera").inner_text()

    # Orbit-drag the canvas: the camera follows (k3d throttles to ~200 ms)
    box = page.locator("#plot canvas").first.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] / 2 + 120, box["y"] + box["height"] / 2 + 40, steps=10
    )
    page.mouse.up()
    expect(page.locator("#camera")).not_to_have_text(before, timeout=10000)

    assert_no_unexpected_errors(errors, failed_requests)
