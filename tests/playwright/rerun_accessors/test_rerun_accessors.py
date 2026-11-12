from __future__ import annotations

import json

import pytest
from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    expose_manager,
)

# The message a real stream-tree click on the "points" entity sends. The
# viewer's canvas-drawn UI can't be hit-tested reliably (see the skipped
# test below), so populated selections are simulated -- the same code path
# (_on_raw_event -> _viewer_event_from_json_str -> selection()) a real
# click's message takes, as docs/widget-guides/rerun/NOTES.md describes.
SELECTION_JSON = json.dumps(
    {
        "type": "selection_change",
        "application_id": "test",
        "recording_id": "rec",
        "segment_id": None,
        "items": [{"type": "entity", "entity_path": "points"}],
    }
)

_SEND_SELECTION_JS = """async (jsonStr) => {
    const models = await Promise.all(
        Object.values(window.widgetManager._models).map((p) => p.catch(() => null))
    );
    const viewer = models.find(
        (m) => m && m.get('_fallback_token') !== undefined && m.get('_panel_states') !== undefined
    );
    if (!viewer) return false;
    viewer.send(jsonStr);
    return true;
}"""


def test_selection_waits_for_the_first_selection(page: Page, local_app) -> None:
    # The viewer's load-time empty selection is ignored (it would clobber a
    # selection kept across a re-render), so the output stays at the
    # placeholder until the user actually selects something
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#viewer .rerun_notebook canvas").first).to_be_visible(
        timeout=90000
    )
    page.wait_for_timeout(3000)  # ample time for a load-time seed, were it emitted
    expect(page.locator("#selection")).to_have_text("(waiting)")

    assert page.evaluate(_SEND_SELECTION_JS, SELECTION_JSON)
    expect(page.locator("#selection")).to_have_text(
        "[EntitySelectionItem]", timeout=30000
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_selection_survives_a_rerender(page: Page, local_app) -> None:
    # A selection is user-interaction state: it must survive a re-render, and
    # the new viewer's load-time empty selection must not clobber it
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#viewer .rerun_notebook canvas").first).to_be_visible(
        timeout=90000
    )
    assert page.evaluate(_SEND_SELECTION_JS, SELECTION_JSON)
    expect(page.locator("#selection")).to_have_text(
        "[EntitySelectionItem]", timeout=30000
    )

    page.click("#rerender")
    expect(page.locator("#viewer .rerun_notebook canvas").first).to_be_visible(
        timeout=90000
    )
    # Give the new viewer's load-time seed ample time to arrive (it lands
    # ~1s after the re-render); only then is its being ignored proven
    page.wait_for_timeout(5000)
    expect(page.locator("#selection")).to_have_text("[EntitySelectionItem]")

    assert_no_unexpected_errors(errors, failed_requests)


@pytest.mark.skip(
    reason=(
        "the viewer's streams tree and viewport are egui-drawn canvas pixels, "
        "not DOM, and hit-testing the 'points' entity by coordinates proved "
        "flaky; populated selections are simulated instead (see above)"
    )
)
def test_selection_follows_stream_tree_clicks(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    canvas = page.locator("#viewer .rerun_notebook canvas").first
    expect(canvas).to_be_visible(timeout=90000)
    page.wait_for_timeout(3000)  # let the viewer's UI finish laying out

    # Clicking a point in the 3D viewport (egui, drawn into the viewer's
    # canvas) selects its entity; the points cluster at the viewport's center
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] * 0.6, box["y"] + box["height"] * 0.5)
    expect(page.locator("#selection")).to_have_text(
        "[EntitySelectionItem]", timeout=30000
    )

    assert_no_unexpected_errors(errors, failed_requests)
