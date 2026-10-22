from __future__ import annotations

import io

import numpy as np
from PIL import Image
from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# The app's points are pure red against a white background
MIN_RED_PIXELS = 50


# True once the plot's canvas matches its output container's size (the canvas
# renders asynchronously after the output/card lay out)
CANVAS_FILLS_OUTPUT_JS = """() => {
  const out = document.querySelector('#fill_plot');
  const canvas = out && out.querySelector('canvas');
  if (!canvas) return false;
  const o = out.getBoundingClientRect();
  const c = canvas.getBoundingClientRect();
  return Math.abs(c.width - o.width) <= 1 && Math.abs(c.height - o.height) <= 1;
}"""


def count_red_pixels(page: Page, selector: str) -> int:
    png = page.locator(selector).first.screenshot()
    rgb = np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(int)
    red = (rgb[..., 0] > 200) & (rgb[..., 1] < 60) & (rgb[..., 2] < 60)
    return int(red.sum())


def wait_for_red_pixels(page: Page, selector: str, timeout_ms: int = 30000) -> None:
    # k3d adds scene objects asynchronously after the canvas exists, so poll
    # until the points have been drawn
    waited = 0
    while count_red_pixels(page, selector) <= MIN_RED_PIXELS:
        assert waited < timeout_ms, f"no scene pixels drawn in {selector}"
        page.wait_for_timeout(250)
        waited += 250


def canvas_size(page: Page, selector: str) -> tuple[float, float]:
    box = page.locator(selector).first.bounding_box()
    assert box is not None
    return box["width"], box["height"]


def test_k3d_renders_webgl_scene(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#fill_plot canvas")).to_have_count(1, timeout=30000)
    width, height = canvas_size(page, "#fill_plot canvas")
    assert width > 0 and height > 0

    # WebGL pixels can't be read back from the canvas itself, so check the
    # composited pixels for the scene's red points
    wait_for_red_pixels(page, "#fill_plot canvas")

    assert_no_unexpected_errors(errors, failed_requests)


def test_k3d_fills_fillable_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#fill_plot canvas")).to_have_count(1, timeout=30000)

    # k3d's default pixel height is 512, but the card is 420px tall (minus
    # padding), so the plot has to shrink to fit
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, timeout=30000)
    card_w, card_h = canvas_size(page, "#fill_card")
    out_w, out_h = canvas_size(page, "#fill_plot")
    assert card_h == 420 and 380 < out_h < card_h and out_w < card_w

    # ... and track the container's width
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, timeout=30000)
    narrow_w, narrow_h = canvas_size(page, "#fill_plot")
    assert narrow_w < out_w - 100 and narrow_h == out_h

    assert_no_unexpected_errors(errors, failed_requests)


def test_k3d_respects_explicit_heights(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#fixed_plot canvas")).to_have_count(1, timeout=30000)
    expect(page.locator("#sized_output canvas")).to_have_count(1, timeout=30000)

    # k3d.plot(height=300): the plot keeps its pixel height
    expect(page.locator("#fixed_plot canvas")).to_have_js_property(
        "clientHeight", 300, timeout=30000
    )
    assert canvas_size(page, "#fixed_plot")[1] == 300

    # output_widget(height="250px"): the plot is sized to the output, rather than
    # overflowing it at k3d's default of 512px
    expect(page.locator("#sized_output canvas")).to_have_js_property(
        "clientHeight", 250, timeout=30000
    )
    assert canvas_size(page, "#sized_output")[1] == 250

    assert_no_unexpected_errors(errors, failed_requests)


def test_k3d_camera_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    canvas = page.locator("#fill_plot canvas")
    expect(canvas).to_have_count(1, timeout=30000)

    # The camera trait is initially the auto-fit position (looking down z)
    expect(page.locator("#camera")).to_contain_text("0, 0, 1]", timeout=30000)
    initial = page.locator("#camera").inner_text()

    # Orbiting the scene syncs the new camera back to Python
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + 100, box["y"] + 100)
    page.mouse.down()
    page.mouse.move(box["x"] + 200, box["y"] + 160, steps=10)
    page.mouse.up()
    expect(page.locator("#camera")).not_to_have_text(initial, timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_k3d_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#fill_plot canvas")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old_canvas = page.locator("#fill_plot canvas").first.element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_canvas, timeout=30000)
        expect(page.locator("#fill_plot canvas")).to_have_count(1, timeout=30000)

    # The old views were all disposed, and the surviving one is the newest
    expect(page.locator("#fill_plot .k3d-plot")).to_have_count(1)
    wait_for_red_pixels(page, "#fill_plot canvas")

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)


def test_k3d_rerender_closes_old_models(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#fill_plot canvas")).to_have_count(1, timeout=30000)
    wait_for_red_pixels(page, "#fill_plot canvas")

    def n_models() -> int:
        # Plots and their objects are all anywidget models
        return sum(1 for m in client_models(page) if m["name"] == "AnyModel")

    initial = n_models()
    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
    wait_for_red_pixels(page, "#fill_plot canvas")

    # Each re-render's old plot (not just its objects) must be closed in the
    # browser, so the model count settles back to the initial one
    waited = 0
    while n_models() != initial:
        assert waited < 10000, (initial, client_models(page))
        page.wait_for_timeout(250)
        waited += 250

    assert_no_unexpected_errors(errors, failed_requests)
