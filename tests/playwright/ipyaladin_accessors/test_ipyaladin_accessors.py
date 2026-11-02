from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The viewer loads its JavaScript from esm.sh and its sky imagery (HiPS tiles)
# from CDS servers; tolerate failed requests to those (tile 404s/CORS blocks
# are environmental), along with the "Failed to load resource" console errors
# they produce (see render_ipyaladin's check_errors)
ALLOWED_REQUEST_FAILURES = ("esm.sh", "alasky", "cds.unistra.fr", "hips")


def check_errors(errors: list[str], failed_requests: list[str]) -> None:
    errors = [
        e
        for e in errors
        if not (
            any(host in e for host in ALLOWED_REQUEST_FAILURES)
            or "Failed to load resource" in e
        )
    ]
    assert_no_unexpected_errors(
        errors, failed_requests, allowed_404s=ALLOWED_REQUEST_FAILURES
    )


def goto_viewer(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(page.locator("#sky .aladin-widget canvas").first).to_be_visible(
        timeout=60000
    )
    # Seeded from the viewer's initial state at render. The viewer snaps the
    # fov to its own zoom steps (2 deg becomes 1.9625...), so match a number,
    # not the constructor value
    expect(page.locator("#target")).to_have_text("83.63,22.01", timeout=60000)
    expect(page.locator("#fov")).to_have_text(
        re.compile(r"^\d+\.\d{4}$"), timeout=60000
    )


def canvas_box(page: Page) -> dict:
    box = page.locator("#sky .aladin-widget canvas").first.bounding_box()
    assert box is not None
    return box


def test_fov_follows_wheel_zoom(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_viewer(page, local_app)
    box = canvas_box(page)

    fov_before = page.locator("#fov").inner_text()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.wheel(0, -400)
    expect(page.locator("#fov")).not_to_have_text(fov_before, timeout=30000)

    check_errors(errors, failed_requests)


def test_target_follows_drag_pan(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_viewer(page, local_app)
    box = canvas_box(page)

    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] / 2 + 100, box["y"] + box["height"] / 2, steps=10
    )
    page.mouse.up()
    expect(page.locator("#target")).not_to_have_text("83.63,22.01", timeout=30000)

    check_errors(errors, failed_requests)


def test_clicked_object_reports_catalog_source(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_viewer(page, local_app)
    expect(page.locator("#clicked_object")).to_have_text("None")
    page.wait_for_timeout(2000)  # let the catalog overlay draw
    box = canvas_box(page)

    # The "center" source sits exactly at the viewer's center
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    expect(page.locator("#clicked_object")).to_have_text("83.63,22.01", timeout=30000)

    check_errors(errors, failed_requests)


def test_selected_objects_follows_rectangle_selection(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    goto_viewer(page, local_app)
    expect(page.locator("#selected_objects")).to_have_text("0")
    page.wait_for_timeout(2000)  # let the catalog overlay draw
    box = canvas_box(page)

    page.click("#arm_selection")
    page.wait_for_timeout(500)
    page.mouse.move(box["x"] + box["width"] * 0.2, box["y"] + box["height"] * 0.2)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] * 0.8, box["y"] + box["height"] * 0.8, steps=10
    )
    page.mouse.up()
    expect(page.locator("#selected_objects")).not_to_have_text("0", timeout=30000)

    check_errors(errors, failed_requests)
