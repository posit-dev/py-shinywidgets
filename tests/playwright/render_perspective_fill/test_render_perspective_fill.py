from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Perspective's own container reserves 5px of padding to the right of and below
# the viewer
PSP_PADDING = 5


def test_perspective_fills_card(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 800})
    page.goto(local_app.url)

    # Perspective ships a large (~6MB) ESM bundle and compiles its WASM engine
    # on first render, so allow generous timeouts
    viewer = page.locator("#viewer perspective-viewer")
    expect(viewer).to_have_count(1, timeout=60000)
    expect(viewer.locator("td").first).to_be_visible(timeout=60000)

    def assert_viewer_fills_container(label: str) -> float:
        container = page.locator("#viewer").bounding_box()
        rendered = viewer.bounding_box()
        assert container is not None and rendered is not None
        print(f"{label}:", {"container": container, "viewer": rendered})
        assert container["height"] > 300
        assert abs(container["width"] - rendered["width"] - PSP_PADDING) <= 1
        assert abs(container["height"] - rendered["height"] - PSP_PADDING) <= 1
        return container["height"]

    tall = assert_viewer_fills_container("800px viewport")

    # ... and it should track the container when the window resizes
    page.set_viewport_size({"width": 700, "height": 600})
    page.wait_for_function(
        "(h) => document.querySelector('#viewer').getBoundingClientRect().height < h",
        arg=tall,
    )
    short = assert_viewer_fills_container("600px viewport")
    assert short < tall

    assert_no_unexpected_errors(errors, failed_requests)
