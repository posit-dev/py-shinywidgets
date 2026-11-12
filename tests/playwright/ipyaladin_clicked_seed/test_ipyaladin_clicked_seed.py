from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The viewer loads its JavaScript from esm.sh and its sky imagery (HiPS tiles)
# from CDS servers; tolerate failed requests to those (tile 404s/CORS blocks
# are environmental), along with the "Failed to load resource" console errors
# they produce (same allowances as tests/playwright/ipyaladin_accessors)
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


def click_viewer_center(page: Page, output_id: str) -> None:
    canvas = page.locator(f"#{output_id} .aladin-widget canvas").first
    expect(canvas).to_be_visible(timeout=60000)
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def test_click_before_gated_first_read_is_reflected_and_stays_per_instance(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    # Both viewers up, with their catalog overlays drawn
    for output_id in ("sky1", "sky2"):
        expect(page.locator(f"#{output_id} .aladin-widget canvas").first).to_be_visible(
            timeout=60000
        )
    page.wait_for_timeout(2000)  # let the catalog overlays draw

    # Click sky1's catalog source before anything has read either
    # clicked_object() accessor (the gated outputs haven't run)
    click_viewer_center(page, "sky1")
    # Wait until the click has synced from browser to server: the sentinel
    # reads the synced trait directly, without touching the accessor
    expect(page.locator("#synced1")).to_have_text("83.63,22.01", timeout=30000)
    expect(page.locator("#gated1")).to_have_text("")

    # The gated first read must report the pre-read click (seeded state), and
    # sky2 -- a separate Aladin instance -- must be unaffected (the frontend
    # retains the click in a per-model trait)
    page.click("#read_clicks")
    expect(page.locator("#gated1")).to_have_text("83.63,22.01", timeout=30000)
    expect(page.locator("#gated2")).to_have_text("None")

    check_errors(errors, failed_requests)
