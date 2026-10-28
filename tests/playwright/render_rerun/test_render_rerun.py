from __future__ import annotations

import base64
import re
import time
from typing import Any

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Must match the markers logged by app.py
PRE_RENDER_MARKER = b"PRE_RENDER_MARKER_7f3a2c"
POST_RENDER_MARKER = b"POST_RENDER_MARKER_9d1e4b"

# Long runs of base64 characters (e.g., the base64-encoded binary buffers
# that shinywidgets sends in place of binary websocket messages). The comm
# payload is itself a JSON string nested in the frame's JSON, so tokens are
# surrounded by escaped quotes (\"); matching bare runs sidesteps that
_B64_TOKEN = re.compile(r"[A-Za-z0-9+/=]{24,}")


def _frame_contains_marker(frame: Any, marker: bytes) -> bool:
    if isinstance(frame, bytes):
        return marker in frame
    for token in _B64_TOKEN.findall(str(frame)):
        try:
            if marker in base64.b64decode(token):
                return True
        except ValueError:
            continue
    return False


def _await_marker(
    page: Page,
    frames: list[Any],
    scanned: list[int],
    marker: bytes,
    timeout: float = 90.0,
) -> None:
    """Poll newly received websocket frames until `marker` shows up in one."""
    deadline = time.monotonic() + timeout
    while True:
        while scanned[0] < len(frames):
            frame = frames[scanned[0]]
            scanned[0] += 1
            if _frame_contains_marker(frame, marker):
                return
        if time.monotonic() > deadline:
            raise AssertionError(
                f"{marker!r} never appeared in the websocket traffic "
                f"({len(frames)} frames received)"
            )
        # wait_for_timeout (unlike time.sleep) pumps Playwright's event loop,
        # so framereceived handlers fire while polling
        page.wait_for_timeout(250)


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
    # The viewer lives in a fixed-height filling container, so the output has
    # usable space to fill
    assert output_box["width"] > 0 and output_box["height"] > 0
    # Viewer() with default 640x480 size is treated as "auto" and tracks the
    # output element's size
    assert abs(inner_box["width"] - output_box["width"]) < 2
    assert abs(inner_box["height"] - output_box["height"]) < 2

    assert_no_unexpected_errors(errors, failed_requests)


def test_rerun_logged_data_reaches_browser(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)

    # shinywidgets base64-encodes binary comm buffers (like the rrd chunks the
    # viewer receives) into websocket text frames, so logged data can be
    # observed by decoding those frames
    frames: list[Any] = []
    page.on(
        "websocket",
        lambda ws: ws.on("framereceived", lambda payload: frames.append(payload)),
    )
    page.goto(local_app.url)

    canvas = page.locator("#viewer .rerun_notebook canvas")
    expect(canvas.first).to_be_visible(timeout=90000)

    scanned = [0]

    # Data logged before the viewer was constructed is replayed to it once it
    # signals it's ready for data (after the wasm viewer boots)
    _await_marker(page, frames, scanned, PRE_RENDER_MARKER)

    # ...and data logged later (to the same mounted viewer's recording) streams
    # to the browser as well
    page.click("#log_more")
    _await_marker(page, frames, scanned, POST_RENDER_MARKER)

    assert_no_unexpected_errors(errors, failed_requests)


def test_rerun_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    canvas = page.locator("#viewer .rerun_notebook canvas")
    expect(canvas).to_have_count(1, timeout=90000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old_canvas = canvas.first.element_handle()
        page.click("#rerender")
        # The re-render must actually replace the viewer: wait for the old
        # view's canvas to detach and the new one to mount (render_count is a
        # separate output and can update before the new viewer is displayed)
        page.wait_for_function("el => !el.isConnected", arg=old_canvas, timeout=90000)
        expect(canvas).to_have_count(1)
        expect(canvas.first).to_be_visible(timeout=90000)
        expect(page.locator("#render_count")).to_have_text(str(i))

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
