from __future__ import annotations

import io
import re

import numpy as np
from PIL import Image
from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# The app's cube is pure red against a white background
MIN_RED_PIXELS = 50


# True once the scene's canvas matches its output container's size (the canvas
# is resized asynchronously after the output/card lay out)
def canvas_fills_output_js(selector: str) -> str:
    return f"""() => {{
      const out = document.querySelector('{selector}');
      const canvas = out && out.querySelector('canvas');
      if (!canvas) return false;
      const o = out.getBoundingClientRect();
      const c = canvas.getBoundingClientRect();
      return Math.abs(c.width - o.width) <= 1 && Math.abs(c.height - o.height) <= 1;
    }}"""


CANVAS_FILLS_OUTPUT_JS = canvas_fills_output_js("#fill_scene")


def count_red_pixels(page: Page, selector: str) -> int:
    try:
        png = page.locator(selector).first.screenshot()
    except Exception:
        # A re-render may swap the canvas out mid-screenshot; treat as not
        # drawn yet and let the polling loop retry
        return 0
    rgb = np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(int)
    red = (rgb[..., 0] > 200) & (rgb[..., 1] < 60) & (rgb[..., 2] < 60)
    return int(red.sum())


def wait_for_red_pixels(page: Page, selector: str, timeout_ms: int = 30000) -> None:
    # WebGL renders asynchronously after the canvas exists, so poll until the
    # cube has actually been drawn
    waited = 0
    while count_red_pixels(page, selector) <= MIN_RED_PIXELS:
        assert waited < timeout_ms, f"no scene pixels drawn in {selector}"
        page.wait_for_timeout(250)
        waited += 250


def canvas_size(page: Page, selector: str) -> tuple[float, float]:
    box = page.locator(selector).first.bounding_box()
    assert box is not None
    return box["width"], box["height"]


def wait_for_settled_height(
    page: Page, selector: str, timeout_ms: int = 10000
) -> float:
    """Poll the canvas height until it's unchanged across 3 samples (250ms apart)."""
    heights: list[float] = []
    waited = 0
    while waited < timeout_ms:
        heights.append(canvas_size(page, selector)[1])
        if len(heights) >= 3 and heights[-1] == heights[-2] == heights[-3]:
            return heights[-1]
        page.wait_for_timeout(250)
        waited += 250
    raise AssertionError(f"{selector} canvas height never settled: {heights}")


def test_pythreejs_renders_webgl_scene(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#fill_scene canvas")).to_have_count(1, timeout=30000)
    width, height = canvas_size(page, "#fill_scene canvas")
    assert width > 0 and height > 0

    # WebGL pixels can't be read back from the canvas itself, so check the
    # composited pixels for the scene's red cube
    wait_for_red_pixels(page, "#fill_scene canvas")

    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_fills_fillable_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#fill_scene canvas")).to_have_count(1, timeout=30000)

    # The default canvas is 200x200, but the card is 420px tall (minus
    # padding), so the canvas has to grow to fit
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, timeout=30000)
    card_w, card_h = canvas_size(page, "#fill_card")
    out_w, out_h = canvas_size(page, "#fill_scene")
    assert card_h == 420 and 380 < out_h < card_h and out_w < card_w

    # ... and track the container's width
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, timeout=30000)
    narrow_w, narrow_h = canvas_size(page, "#fill_scene")
    assert narrow_w < out_w - 100 and narrow_h == out_h

    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_respects_explicit_sizes(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#fixed_scene canvas")).to_have_count(1, timeout=30000)
    expect(page.locator("#sized_output canvas")).to_have_count(1, timeout=30000)

    # Renderer(width=400, height=300): the scene keeps its pixel size
    expect(page.locator("#fixed_scene canvas")).to_have_js_property(
        "clientWidth", 400, timeout=30000
    )
    expect(page.locator("#fixed_scene canvas")).to_have_js_property(
        "clientHeight", 300, timeout=30000
    )
    # (the output wraps the canvas, plus a few px of inline-canvas line gap)
    assert abs(canvas_size(page, "#fixed_scene")[1] - 300) <= 6

    # output_widget(height="250px"): the scene is sized to the output, rather
    # than overflowing it at the 200px default
    expect(page.locator("#sized_output canvas")).to_have_js_property(
        "clientHeight", 250, timeout=30000
    )
    assert canvas_size(page, "#sized_output")[1] == 250

    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_settles_in_unfillable_containers(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # In a container whose height comes from its content (plain page_fluid, or
    # a card with no height), sizing the canvas to the output must reach a
    # fixed point -- previously the canvas grew by a few px on every
    # ResizeObserver fire, growing the output again, until the canvas died
    for sel in ("#unfillable_scene", "#unfillable_card_scene"):
        expect(page.locator(f"{sel} canvas")).to_have_count(1, timeout=30000)
        settled = wait_for_settled_height(page, f"{sel} canvas")
        assert settled > 0
        # Once settled, it stays put
        page.wait_for_timeout(1000)
        assert canvas_size(page, f"{sel} canvas")[1] == settled

    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_camera_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    canvas = page.locator("#fill_scene canvas")
    expect(canvas).to_have_count(1, timeout=30000)

    # The camera starts on the z axis, looking at the origin
    expect(page.locator("#camera")).to_contain_text("0.0, 0.0, 3.0", timeout=30000)
    initial = page.locator("#camera").inner_text()

    # Orbiting the scene syncs the new camera position back to Python
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + 100, box["y"] + 100)
    page.mouse.down()
    page.mouse.move(box["x"] + 200, box["y"] + 160, steps=10)
    page.mouse.up()
    expect(page.locator("#camera")).not_to_have_text(initial, timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_camera_swap_tracks_container_aspect(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#fill_scene canvas")).to_have_count(1, timeout=30000)
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, timeout=30000)

    # The initial camera's aspect tracks the (much wider than tall) container.
    # Wait past the camera's default (1.0): the browser may still be holding the
    # container-driven aspect back, behind an unacked message.
    expect(page.locator("#camera_aspect")).to_have_text(
        re.compile(r"^(?!1\.0000$)\d+\.\d{4}$"), timeout=30000
    )
    initial_text = page.locator("#camera_aspect").inner_text()
    assert float(initial_text) != 1.0

    # Replacing the camera in place applies the current container size to the
    # replacement immediately, even though the container size is unchanged
    # (the replacement's default aspect is 1.0). Record output mutations before
    # clicking so the swap's round-trip can be observed reliably: the output
    # briefly shows the replacement's default aspect ("1.0000") before the
    # browser applies the container aspect, and that window is too short for
    # expect()'s polling to catch. (Asserting initial_text right after the
    # click is a no-op -- the output still shows the pre-swap value -- which
    # would let the resize below reach the browser before the camera change
    # does.)
    page.evaluate(
        """() => {
          const el = document.querySelector('#camera_aspect');
          window.__cameraAspectTouched = false;
          new MutationObserver(() => { window.__cameraAspectTouched = true; })
            .observe(el, { childList: true, characterData: true, subtree: true });
        }"""
    )
    page.click("#swap_camera")
    page.wait_for_function("() => window.__cameraAspectTouched", timeout=30000)
    expect(page.locator("#camera_aspect")).to_have_text(initial_text, timeout=30000)
    expect(page.locator("#swapped_camera_aspect")).to_have_text(
        initial_text, timeout=30000
    )

    # Later resizes update the replacement camera's aspect ...
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, timeout=30000)
    expect(page.locator("#camera_aspect")).not_to_have_text(initial_text, timeout=30000)
    resized = float(page.locator("#camera_aspect").inner_text())
    out_w, out_h = canvas_size(page, "#fill_scene")
    assert abs(resized - out_w / out_h) < 0.05

    # ... while the swapped-out camera's aspect stays where it was (resize
    # management moved to the replacement rather than the stale camera). Give
    # a stale update a chance to round-trip before reading.
    page.wait_for_timeout(1500)
    assert page.locator("#swapped_camera_aspect").inner_text() == initial_text

    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_cached_renderer_keeps_filling_after_rerender(
    page: Page, local_app
) -> None:
    # Regression: a default-sized Renderer cached with session_lifetime() and
    # returned on a later render must keep filling -- the container size the
    # browser synced back to Python is not an explicit user size
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    canvas = page.locator("#cached_scene canvas")
    expect(canvas).to_have_count(1, timeout=30000)
    page.wait_for_function(canvas_fills_output_js("#cached_scene"), timeout=30000)
    wide_w, _ = canvas_size(page, "#cached_scene canvas")

    # Resize the browser, which syncs the container size back to the Python
    # Renderer's width/height traits
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(canvas_fills_output_js("#cached_scene"), timeout=30000)

    # The re-render returns the same cached Renderer; it must still fill.
    # Identify the old view by its root element, not its <canvas>: pythreejs's
    # RendererPool recycles freed canvas elements into new views (e.g. the
    # fill_scene view re-rendered by the same click), so a canvas can stay
    # connected forever under a different output.
    old_view = page.locator("#cached_scene > .jupyter-threejs").first.element_handle()
    page.click("#rerender")
    page.wait_for_function("(el) => !el.isConnected", arg=old_view, timeout=30000)
    expect(canvas).to_have_count(1, timeout=30000)
    page.wait_for_function(canvas_fills_output_js("#cached_scene"), timeout=30000)

    # ... and keep tracking the container afterwards
    page.set_viewport_size({"width": 900, "height": 900})
    page.wait_for_function(canvas_fills_output_js("#cached_scene"), timeout=30000)
    final_w, _ = canvas_size(page, "#cached_scene canvas")
    assert final_w > wide_w - 10

    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_cached_renderer_keeps_user_camera_aspect(
    page: Page, local_app
) -> None:
    # Regression: an explicit camera aspect must survive a re-render of a
    # cached Renderer -- the new view must not adopt the user's aspect as the
    # managed baseline and overwrite it with the container ratio on resize
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    canvas = page.locator("#cached_scene canvas")
    expect(canvas).to_have_count(1, timeout=30000)
    page.wait_for_function(canvas_fills_output_js("#cached_scene"), timeout=30000)
    # Wait for Python to see the container-driven aspect (the camera starts at
    # 1.0): until then the browser may still hold it back, behind an unacked
    # message, and send it after the click below, where it would overwrite 1.5
    # (the same last-writer-wins race as a busy Jupyter kernel)
    expect(page.locator("#cached_camera_aspect")).to_have_text(
        re.compile(r"^(?!1\.0000$)\d+\.\d{4}$"), timeout=30000
    )

    # The container-driven aspect is nowhere near 1.5 (the card is much wider
    # than tall), so this is unambiguously a user-set value
    page.click("#set_aspect")
    expect(page.locator("#cached_camera_aspect")).to_have_text("1.5000", timeout=30000)

    # The re-render returns the same cached Renderer; its new view must leave
    # the user's aspect alone
    old_view = page.locator("#cached_scene > .jupyter-threejs").first.element_handle()
    page.click("#rerender")
    page.wait_for_function("(el) => !el.isConnected", arg=old_view, timeout=30000)
    expect(canvas).to_have_count(1, timeout=30000)
    page.wait_for_function(canvas_fills_output_js("#cached_scene"), timeout=30000)

    # Give a (buggy) aspect overwrite a chance to round-trip to Python
    page.wait_for_timeout(1500)
    expect(page.locator("#cached_camera_aspect")).to_have_text("1.5000")

    # Later resizes still fill the container, but keep the user's aspect
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(canvas_fills_output_js("#cached_scene"), timeout=30000)
    page.wait_for_timeout(1500)
    expect(page.locator("#cached_camera_aspect")).to_have_text("1.5000")

    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_respects_non_fillable_output(page: Page, local_app) -> None:
    # Regression: output_widget(fillable=False) without an explicit height
    # leaves a default-sized Renderer at its own (200x200) size instead of
    # stretching the canvas to the output's full width; an explicit height
    # still sizes the canvas to the output
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#nonfillable_scene canvas")).to_have_count(1, timeout=30000)
    expect(page.locator("#sized_nonfillable canvas")).to_have_count(1, timeout=30000)

    expect(page.locator("#nonfillable_scene canvas")).to_have_js_property(
        "clientWidth", 200, timeout=30000
    )
    expect(page.locator("#nonfillable_scene canvas")).to_have_js_property(
        "clientHeight", 200, timeout=30000
    )

    expect(page.locator("#sized_nonfillable canvas")).to_have_js_property(
        "clientHeight", 250, timeout=30000
    )
    assert canvas_size(page, "#sized_nonfillable")[1] == 250

    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#fill_scene canvas")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        # Identify the old view by its root element, not its <canvas>:
        # pythreejs's RendererPool recycles freed canvas elements into new
        # views (e.g. cached_scene's, re-rendered by the same click), so a
        # canvas can stay connected forever under a different output.
        old_view = page.locator("#fill_scene > .jupyter-threejs").first.element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_view, timeout=30000)
        expect(page.locator("#fill_scene canvas")).to_have_count(1, timeout=30000)

    # The old views were all disposed, and the surviving one is the newest
    expect(page.locator("#fill_scene > .jupyter-threejs")).to_have_count(1)
    wait_for_red_pixels(page, "#fill_scene canvas")

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)


def test_pythreejs_rerender_closes_old_models(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#fill_scene canvas")).to_have_count(1, timeout=30000)
    wait_for_red_pixels(page, "#fill_scene canvas")

    # The renderer, scene, camera, controls, mesh, geometry, and material are
    # all separate models; only fill_scene re-renders, so the total settles
    def n_models() -> int:
        return len(client_models(page))

    initial = n_models()
    assert initial > 0
    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
    wait_for_red_pixels(page, "#fill_scene canvas")

    # Each re-render's old scene graph must be closed in the browser, so the
    # model count settles back to the initial one
    waited = 0
    while n_models() != initial:
        assert waited < 10000, (initial, client_models(page))
        page.wait_for_timeout(250)
        waited += 250

    assert_no_unexpected_errors(errors, failed_requests)
