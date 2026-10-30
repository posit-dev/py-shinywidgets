from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    expose_manager,
    wait_for_stable_model_view_count,
)

# Exporting the scene (server-side) and booting the embedded vtk.js client
# (browser-side) are both slow on first render
READY_TIMEOUT = 60000

# Bounding boxes of the output container and the pyvista iframe inside it
BOXES_JS = """(sel) => {
  const out = document.querySelector(sel);
  const ifr = out && out.querySelector('iframe.pyvista');
  if (!ifr) return null;
  const r = (e) => { const b = e.getBoundingClientRect(); return [b.width, b.height]; };
  return { out: r(out), ifr: r(ifr) };
}"""


def test_pyvista_renders_interactive_scene(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # The widget is an iframe whose srcdoc embeds a client-side vtk.js scene
    iframe = page.locator("#plot iframe.pyvista")
    expect(iframe).to_have_count(1, timeout=READY_TIMEOUT)
    canvas = page.frame_locator("#plot iframe.pyvista").locator("canvas").first
    expect(canvas).to_be_visible(timeout=READY_TIMEOUT)
    box = canvas.bounding_box()
    assert box is not None and box["width"] > 0 and box["height"] > 0

    # Camera interaction is client-side: dragging rotates the scene
    before = iframe.screenshot()
    ibox = iframe.bounding_box()
    assert ibox is not None
    cx, cy = ibox["x"] + ibox["width"] / 2, ibox["y"] + ibox["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 150, cy + 60, steps=10)
    page.mouse.up()
    page.wait_for_timeout(1000)
    assert iframe.screenshot() != before

    assert_no_unexpected_errors(errors, failed_requests)


def test_pyvista_fills_container_and_respects_explicit_height(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 800})
    page.goto(local_app.url)
    expect(page.locator("#plot iframe.pyvista")).to_have_count(1, timeout=READY_TIMEOUT)
    expect(page.locator("#plot_fixed iframe.pyvista")).to_have_count(
        1, timeout=READY_TIMEOUT
    )

    def boxes(sel: str) -> dict[str, list[float]]:
        # Wait for fill layout to settle (the iframe appears before the
        # container reaches its final size)
        page.wait_for_function(
            f"""(() => {{
              const b = {BOXES_JS};
              const r = b('{sel}');
              return r !== null && r.out[1] > 50 && r.ifr[1] > 50;
            }})()""",
            timeout=READY_TIMEOUT,
        )
        return page.evaluate(BOXES_JS, sel)

    # In the fillable card, the iframe fills the output container (and tracks
    # it across a window resize)
    # (the iframe carries a 1px border, so allow a few px of slack)
    def fills(b: dict[str, list[float]]) -> bool:
        return all(0 <= o - i <= 6 for o, i in zip(b["out"], b["ifr"], strict=True))

    wide = boxes("#plot")
    assert fills(wide)
    # (keep the viewport tall: a shorter one is consumed by the fixed-height
    # sibling, leaving the card nothing to fill)
    page.set_viewport_size({"width": 640, "height": 800})
    narrow = boxes("#plot")
    assert narrow["ifr"][0] < wide["ifr"][0]
    assert fills(narrow)

    # An explicit output_widget(height=...) is respected
    fixed = boxes("#plot_fixed")
    assert fixed["out"][1] == 300
    assert 300 - 6 <= fixed["ifr"][1] <= 300

    assert_no_unexpected_errors(errors, failed_requests)


def test_pyvista_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    iframe = page.locator("#plot iframe.pyvista")
    canvas = page.frame_locator("#plot iframe.pyvista").locator("canvas").first
    expect(iframe).to_have_count(1, timeout=READY_TIMEOUT)
    expect(canvas).to_be_visible(timeout=READY_TIMEOUT)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        previous = iframe.element_handle()
        page.click("#rerender")
        # render_count is a separate output that can update before the
        # replacement view arrives; wait for the old view's iframe to detach
        # and the new one to render its scene, so the cleanup assertions
        # below can't be satisfied by a stale view
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function(
            "(el) => !el.isConnected", arg=previous, timeout=READY_TIMEOUT
        )
        expect(canvas).to_be_visible(timeout=READY_TIMEOUT)

    # Re-rendering replaces the widget; the old view must be disposed, both
    # in the DOM and in the manager's live-view registry (one HTMLModel view
    # per output: #plot + #plot_fixed)
    expect(page.locator("#plot > .lm-Widget")).to_have_count(1)
    expect(iframe).to_have_count(1)
    assert wait_for_stable_model_view_count(page, "HTMLModel", expected=2) == 2

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
