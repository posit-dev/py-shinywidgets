from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    wait_for_red_pixels,
)

# An ipyvolume figure view renders two stacked canvases (the WebGL scene and
# a 2D selection overlay) inside .ipyvolume-canvas-container
CANVAS_CONTAINER = ".ipyvolume-canvas-container"

# True once the figure's canvas fills its output container (the output's
# height minus the figure's toolbar). The canvas is resized asynchronously
# once the output/card lay out.
CANVAS_FILLS_OUTPUT_JS = """(id) => {
  const out = document.querySelector(id);
  const view = out && out.querySelector('.lm-Widget');
  const canvas = out && out.querySelector('canvas');
  if (!view || !canvas) return false;
  const toolbar = view.firstElementChild;
  const c = canvas.getBoundingClientRect();
  return (
    Math.abs(c.width - out.clientWidth) <= 1 &&
    Math.abs(c.height - (out.clientHeight - toolbar.offsetHeight)) <= 1
  );
}"""


# True once the figure's canvas fills its explicitly sized widget view (the
# view's Layout height, minus the figure's toolbar). Used when the view is
# smaller than its (filling) output container.
CANVAS_FILLS_VIEW_JS = """(id) => {
  const out = document.querySelector(id);
  const view = out && out.querySelector('.lm-Widget');
  const canvas = out && out.querySelector('canvas');
  if (!view || !canvas) return false;
  const toolbar = view.firstElementChild;
  const c = canvas.getBoundingClientRect();
  return Math.abs(c.height - (view.clientHeight - toolbar.offsetHeight)) <= 1;
}"""


def canvas_size(page: Page, selector: str) -> tuple[float, float]:
    box = page.locator(selector).first.bounding_box()
    assert box is not None
    return box["width"], box["height"]


def test_ipyvolume_renders_webgl_scene(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator(f"#fill_plot {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )
    width, height = canvas_size(page, "#fill_plot canvas")
    assert width > 0 and height > 0

    wait_for_red_pixels(page, "#fill_plot canvas")

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipyvolume_fills_fillable_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    expect(page.locator(f"#fill_plot {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )

    # ipyvolume's default canvas is 400x500px, but the card is 420px tall
    # (minus padding), so the canvas has to be resized to fit
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="#fill_plot", timeout=30000)
    card_w, card_h = canvas_size(page, "#fill_card")
    out_w, out_h = canvas_size(page, "#fill_plot")
    assert card_h == 420 and 350 < out_h < card_h and out_w < card_w

    # ... and track the container's width
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="#fill_plot", timeout=30000)
    narrow_w, narrow_h = canvas_size(page, "#fill_plot")
    assert narrow_w < out_w - 100 and narrow_h == out_h

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipyvolume_respects_explicit_heights(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator(f"#fixed_plot {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator(f"#sized_output {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator(f"#sized_layout {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )

    # ipv.figure(width=400, height=300): the figure keeps its pixel size
    expect(page.locator("#fixed_plot canvas").first).to_have_js_property(
        "clientHeight", 300, timeout=30000
    )
    assert canvas_size(page, "#fixed_plot canvas")[1] == 300

    # output_widget(height="250px") and widget.layout = Layout(height="300px"):
    # the canvas is sized to the space it's given, rather than drawn at
    # ipyvolume's default of 500px and clipped
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="#sized_output", timeout=30000)
    assert canvas_size(page, "#sized_output")[1] == 250
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="#sized_layout", timeout=30000)
    assert canvas_size(page, "#sized_layout")[1] == 300

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipyvolume_explicit_size_inside_sized_output(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator(f"#sized_fixed_plot {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )

    # An explicit figure size (400x300) inside output_widget(height="250px"):
    # the figure keeps its pixel size (the output clips it) rather than the
    # output's CSS height overwriting it
    expect(page.locator("#sized_fixed_plot canvas").first).to_have_js_property(
        "clientHeight", 300, timeout=30000
    )
    assert canvas_size(page, "#sized_fixed_plot")[1] == 250
    assert canvas_size(page, "#sized_fixed_plot canvas")[1] == 300

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipyvolume_viewport_relative_layout_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 800, "height": 1000})
    page.goto(local_app.url)
    expect(page.locator(f"#vh_layout {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )

    # Layout(height="50vh") inside a fixed-height output: the canvas tracks
    # the view, which is ~500px tall at a 1000px viewport ...
    page.wait_for_function(CANVAS_FILLS_VIEW_JS, arg="#vh_layout", timeout=30000)
    view_h = canvas_size(page, "#vh_layout .lm-Widget")[1]
    assert 490 < view_h < 510

    # ... and still tracks it when the viewport (but neither the output's
    # size nor the view's inline style) changes
    page.set_viewport_size({"width": 800, "height": 600})
    page.wait_for_function(CANVAS_FILLS_VIEW_JS, arg="#vh_layout", timeout=30000)
    view_h = canvas_size(page, "#vh_layout .lm-Widget")[1]
    assert 290 < view_h < 310

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipyvolume_layout_height_inside_fillable_card(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator(f"#sized_layout_card {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )

    # The widget's Layout(height="300px") sizes the view to 300px, but the
    # output stays a fill item in the card and is taller than that. The
    # canvas must be sized to the widget view, not the output -- otherwise it
    # overflows/is clipped by the 300px widget.
    page.wait_for_function(
        CANVAS_FILLS_VIEW_JS, arg="#sized_layout_card", timeout=30000
    )
    out_h = canvas_size(page, "#sized_layout_card")[1]
    canvas_h = canvas_size(page, "#sized_layout_card canvas")[1]
    assert out_h > 300
    assert canvas_h < 300

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipyvolume_selection_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator(f"#fill_plot {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )
    expect(page.locator("#selection")).to_have_text("none", timeout=30000)

    # Holding Ctrl over the canvas switches to selection mode (the app's
    # figure uses the rectangle selector) -- ipyvolume only honors the
    # keydown while the mouse hovers the canvas, so hover first. Mouse up
    # sends the selection to Python.
    box = page.locator("#fill_plot canvas").first.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + 50, box["y"] + 50)
    page.keyboard.down("Control")
    page.mouse.down()
    page.mouse.move(box["x"] + 200, box["y"] + 150, steps=10)
    page.mouse.up()
    page.keyboard.up("Control")

    expect(page.locator("#selection")).to_contain_text("rectangle", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipyvolume_camera_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator(f"#fill_plot {CANVAS_CONTAINER}")).to_have_count(
        1, timeout=30000
    )
    page.wait_for_timeout(500)
    initial = page.locator("#camera").inner_text()

    # Orbiting the scene syncs the new camera position back to Python
    box = page.locator("#fill_plot canvas").first.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + 100, box["y"] + 100)
    page.mouse.down()
    page.mouse.move(box["x"] + 220, box["y"] + 180, steps=10)
    page.mouse.up()
    expect(page.locator("#camera")).not_to_have_text(initial, timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)
