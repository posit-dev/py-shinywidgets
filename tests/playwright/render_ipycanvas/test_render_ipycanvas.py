from __future__ import annotations

import time

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)

# The ipycanvas view's root element IS the <canvas> (it carries the
# .lm-Widget class itself, there is no wrapper)
CANVAS = "#canvas canvas.lm-Widget"

# Bounding boxes of the output container and the canvas element inside it
BOXES_JS = """(sel) => {
  const out = document.querySelector(sel);
  const canvas = out && out.querySelector('canvas');
  if (!out || !canvas) return null;
  const o = out.getBoundingClientRect();
  const c = canvas.getBoundingClientRect();
  const p = out.parentElement.getBoundingClientRect();
  return {
    out: { x: o.x, y: o.y, width: o.width, height: o.height },
    canvas: { x: c.x, y: c.y, width: c.width, height: c.height },
    parent: { x: p.x, y: p.y, width: p.width, height: p.height },
  };
}"""

# A fingerprint of the canvas' top-left region (the animation strip at the
# bottom is excluded, so only newly drawn image content changes this)
TOP_LEFT_PIXELS_JS = """(sel) => {
  const canvas = document.querySelector(sel);
  if (!canvas) return null;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  const d = ctx.getImageData(0, 0, Math.min(100, canvas.width), Math.min(60, canvas.height)).data;
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) sum = (sum + d[i] * 3 + d[i + 1] * 5 + d[i + 2] * 7) % 1000000007;
  return sum;
}"""


def test_ipycanvas_renders_and_draws(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator(CANVAS)).to_have_count(1, timeout=30000)
    # The render function's drawing (a rect + an image sent as a binary
    # buffer) survives the trip to the browser
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#canvas", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipycanvas_fill_centers_canvas_at_natural_size(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 1200})
    page.goto(local_app.url)

    expect(page.locator(CANVAS)).to_have_count(1, timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#canvas", timeout=30000)

    boxes = page.evaluate(BOXES_JS, "#canvas")
    assert boxes is not None
    out, canvas, parent = boxes["out"], boxes["canvas"], boxes["parent"]

    # The output fills its (definite-height) container (up to the card
    # body's padding)...
    assert 0 <= parent["height"] - out["height"] < 40
    assert out["height"] > 400  # much taller than the canvas
    # ...but the canvas keeps its natural pixel size (300x200) -- filling the
    # container centers it rather than stretching the bitmap
    assert canvas["width"] == 300
    assert canvas["height"] == 200
    # Centered within the output (both axes)
    assert abs((canvas["x"] + canvas["width"] / 2) - (out["x"] + out["width"] / 2)) < 1
    assert (
        abs((canvas["y"] + canvas["height"] / 2) - (out["y"] + out["height"] / 2)) < 1
    )

    # An explicit output height is respected (no filling)
    fixed = page.evaluate(BOXES_JS, "#canvas_fixed")
    assert fixed is not None
    assert fixed["out"]["height"] == 150
    assert fixed["canvas"]["height"] == 200  # still natural size

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipycanvas_mouse_events_roundtrip_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    canvas = page.locator(CANVAS)
    expect(canvas).to_have_count(1, timeout=30000)
    expect(page.locator("#mouse_pos")).to_have_text("")

    box = canvas.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + 30, box["y"] + 40)
    expect(page.locator("#mouse_pos")).to_have_text("30,40", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipycanvas_animation_frames_reach_browser(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator(CANVAS)).to_have_count(1, timeout=30000)

    # Frames are driven by a Python asyncio task (via invalidate_later); both
    # the frame counter (a reactive value) and the actual canvas pixels must
    # keep advancing
    expect(page.locator("#frame")).not_to_have_text("0", timeout=30000)
    frame_before = int(page.locator("#frame").inner_text())
    time.sleep(1)
    frame_after = int(page.locator("#frame").inner_text())
    assert frame_after > frame_before

    # The animation strip (bottom 40px of the canvas) must keep changing too
    anim_strip = """(sel) => {
      const canvas = document.querySelector(sel);
      const ctx = canvas.getContext('2d');
      const d = ctx.getImageData(0, canvas.height - 40, canvas.width, 40).data;
      let sum = 0;
      for (let i = 0; i < d.length; i += 4) sum = (sum + d[i] + d[i + 1] + d[i + 2]) % 1000000007;
      return sum;
    }"""
    strip_before = page.evaluate(anim_strip, CANVAS)
    time.sleep(0.5)
    strip_after = page.evaluate(anim_strip, CANVAS)
    assert strip_before != strip_after

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipycanvas_image_transport(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator(CANVAS)).to_have_count(1, timeout=30000)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#canvas", timeout=30000)

    before = page.evaluate(TOP_LEFT_PIXELS_JS, CANVAS)
    t0 = time.perf_counter()
    page.click("#draw_image")
    # A 300x200 random-noise image (240KB raw, base64-encoded over the
    # websocket) drawn with put_image_data
    page.wait_for_function(
        f"(sel) => {{ const f = {TOP_LEFT_PIXELS_JS}; return f(sel) !== null && f(sel) !== {before}; }}",
        arg=CANVAS,
        timeout=30000,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"\nput_image_data (300x200 RGBA noise) click-to-pixels: {elapsed_ms:.0f} ms")

    assert_no_unexpected_errors(errors, failed_requests)


def test_ipycanvas_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator(CANVAS)).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator(CANVAS)).to_have_count(1)

    # Re-rendering replaces the widget; the old view must be disposed
    expect(page.locator("#canvas .lm-Widget")).to_have_count(1)
    page.wait_for_function(CANVAS_HAS_PIXELS_JS, arg="#canvas", timeout=30000)

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)
