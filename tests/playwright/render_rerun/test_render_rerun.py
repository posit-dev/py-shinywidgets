from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors


def test_rerun_renders_canvas(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # The rerun viewer is a Wasm/WebGL app; assert its canvas exists and has
    # non-zero dimensions (the wasm can take a while to boot under load)
    canvas = page.locator("#viewer .rerun_notebook canvas")
    expect(canvas.first).to_be_visible(timeout=90000)
    box = canvas.first.bounding_box()
    assert box is not None and box["width"] > 0 and box["height"] > 0

    assert_no_unexpected_errors(errors, failed_requests)


def test_rerun_default_size_fills_output(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    inner = page.locator("#viewer .rerun_notebook > div")
    expect(inner).to_have_count(1, timeout=90000)
    output_box = page.locator("#viewer").bounding_box()
    inner_box = inner.bounding_box()
    assert output_box is not None and inner_box is not None
    # Viewer(width="auto", height="auto") tracks the output element's size
    assert abs(inner_box["width"] - output_box["width"]) < 2
    assert abs(inner_box["height"] - output_box["height"]) < 2

    assert_no_unexpected_errors(errors, failed_requests)


def test_rerun_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#viewer .rerun_notebook")).to_have_count(1, timeout=90000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    # Re-rendering replaces the widget, but the old view must be disposed
    # (i.e., no accumulation of viewers/canvases)
    expect(page.locator("#viewer .rerun_notebook")).to_have_count(1)
    expect(page.locator("#viewer .rerun_notebook canvas")).to_have_count(1)

    assert_no_unexpected_errors(errors, failed_requests)


def test_rerun_viewer_event_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    canvas = page.locator("#viewer .rerun_notebook canvas")
    expect(canvas.first).to_be_visible(timeout=90000)
    # Clicking the viewer produces a SelectionChangeEvent (via
    # Viewer.on_event() -> comm message -> reactive.Value)
    canvas.first.click()
    expect(page.locator("#viewer_event")).to_contain_text("Event", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)
