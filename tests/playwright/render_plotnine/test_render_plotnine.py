from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
)

# Sizes (CSS px) of an output, its ipympl figure canvas, and the widget's
# chrome around the canvas: the footer (which shows cursor coordinates) and
# the canvas div's vertical margins (which mpl auto-resize subtracts from the
# space it gives the figure, so they're part of the output's height budget)
BOXES_JS = """(sel) => {
  const out = document.querySelector(sel);
  const canvas = out && out.querySelector('.jupyter-matplotlib-canvas-div canvas');
  if (!canvas) return null;
  const footer = out.querySelector('.jupyter-matplotlib-footer');
  const style = getComputedStyle(canvas.closest('.jupyter-matplotlib-canvas-div'));
  const o = out.getBoundingClientRect();
  const c = canvas.getBoundingClientRect();
  return {
    output: [o.width, o.height],
    canvas: [c.width, c.height],
    footer: footer ? footer.getBoundingClientRect().height : 0,
    vmargin: parseFloat(style.marginTop) + parseFloat(style.marginBottom),
  };
}"""

# True once the figure canvas spans the output (less the chrome) within 2px
FILLS_JS = f"""(sel) => {{
  const b = ({BOXES_JS})(sel);
  return !!b
    && Math.abs(b.canvas[0] - b.output[0]) <= 2
    && Math.abs(b.canvas[1] + b.footer + b.vmargin - b.output[1]) <= 2;
}}"""


def test_plotnine_renders(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#plot canvas").first).to_be_visible(timeout=30000)
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#plot")
    # plotnine closes its pyplot figure, so "Figure <n>" would be meaningless
    header = page.locator("#plot .jupyter-matplotlib-header")
    expect(header).to_have_count(1)
    assert header.evaluate("(el) => getComputedStyle(el).display") == "none"

    assert_no_unexpected_errors(errors, failed_requests)


def test_plotnine_fills_and_relayouts(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 1000, "height": 800})
    page.goto(local_app.url)

    for viewport in [(1000, 800), (800, 1000), (1400, 500)]:
        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        page.wait_for_function(FILLS_JS, arg="#plot", timeout=30000)
        boxes = page.evaluate(BOXES_JS, "#plot")
        w, h = round(boxes["canvas"][0]), round(boxes["canvas"][1])

        # Python-side: the figure was resized to the canvas size and redrawn
        # (ipympl sends the resize to Python, and the redraw request after it,
        # asynchronously, so poll), and plotnine re-laid it out so no text
        # (legend, axis labels, title) is clipped
        report = check_layout_until_size(page, w, h)
        assert "clipped=[]" in report, f"{report} at viewport {viewport}"
        texts = re.search(r"texts=(\d+)", report)
        assert texts is not None and int(texts[1]) > 10

    assert_no_unexpected_errors(errors, failed_requests)


def check_layout_until_size(page: Page, w: int, h: int) -> str:
    layout = page.locator("#layout")
    report = ""
    for _ in range(20):
        prev = re.search(r"n=(\d+)", layout.inner_text())
        n = int(prev[1]) + 1 if prev else 1
        page.click("#check_layout")
        expect(layout).to_contain_text(f"n={n} ")
        report = layout.inner_text()
        size = re.search(r"size=(\d+)x(\d+)", report)
        assert size is not None
        resized = abs(int(size[1]) - w) <= 2 and abs(int(size[2]) - h) <= 2
        if resized and "stale=False" in report:
            return report
        page.wait_for_timeout(250)
    raise AssertionError(f"figure never redrawn at the {w}x{h} canvas: {report}")


def test_plotnine_hover_does_not_clip_plot(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    page.wait_for_function(FILLS_JS, arg="#plot", timeout=30000)

    # ipympl's footer (the cursor-coordinates readout) is empty until the first
    # hover; if it then took up space, it'd push the bottom of the plot (the
    # x-axis title) out of the output
    canvas = page.locator("#plot .jupyter-matplotlib-canvas-div canvas").last
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] * 0.4, box["y"] + box["height"] * 0.5)
    page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
    page.wait_for_timeout(1000)

    boxes = page.evaluate(BOXES_JS, "#plot")
    assert boxes["footer"] == 0, boxes
    canvas_bottom = boxes["canvas"][1] + boxes["vmargin"]
    assert abs(canvas_bottom - boxes["output"][1]) <= 2, boxes

    assert_no_unexpected_errors(errors, failed_requests)


def test_plotnine_explicit_height_respected(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#fixed canvas").first).to_be_visible(timeout=30000)
    boxes = page.evaluate(BOXES_JS, "#fixed")

    # The output keeps its explicit height, and (since it doesn't fill) the
    # plot is drawn at its theme(figure_size=(4, 2)) at plotnine's 100 dpi
    assert round(boxes["output"][1]) == 250
    assert [round(x) for x in boxes["canvas"]] == [400, 200]

    assert_no_unexpected_errors(errors, failed_requests)


def test_plotnine_rerender_releases_old_views(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#plot canvas").first).to_be_visible(timeout=30000)
    page.wait_for_function(FILLS_JS, arg="#plot", timeout=30000)
    n_canvases = page.locator("#plot canvas").count()
    initial_views = sum(m["views"] for m in client_models(page))

    for i in range(1, 4):
        old_canvas = page.locator("#plot canvas").first.element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_canvas)
        page.wait_for_function(FILLS_JS, arg="#plot", timeout=30000)

    expect(page.locator("#plot canvas")).to_have_count(n_canvases)
    assert sum(m["views"] for m in client_models(page)) == initial_views
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#plot")

    assert_no_unexpected_errors(errors, failed_requests)


def test_plotnine_click_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    page.wait_for_function(FILLS_JS, arg="#plot", timeout=30000)
    expect(page.locator("#clicked")).to_have_text("clicks=0")

    # A click on the figure reaches matplotlib's event handling in Python
    # (ipympl -> shinywidgets comm -> mpl_connect callback -> reactive value)
    box = page.locator(
        "#plot .jupyter-matplotlib-canvas-div canvas"
    ).last.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] * 0.4, box["y"] + box["height"] * 0.5)
    expect(page.locator("#clicked")).to_have_text("clicks=1", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)
