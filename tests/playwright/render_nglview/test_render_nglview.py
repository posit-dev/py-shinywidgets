from __future__ import annotations

import io

from PIL import Image
from playwright.sync_api import Locator, Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    collect_errors,
    expose_manager,
    wait_for_stable_view_count,
)

# Size (in CSS px) of an element and the canvas nglview drew inside it
SIZES_JS = """(id) => {
  const out = document.getElementById(id);
  const canvas = out.querySelector('canvas');
  const o = out.getBoundingClientRect();
  const c = canvas.getBoundingClientRect();
  return { out: [o.width, o.height], canvas: [c.width, c.height] };
}"""

MIN_DRAWN_PIXELS = 100

# True once nglview's canvas matches the size of its output element
CANVAS_FILLS_OUTPUT_JS = """(id) => {
  const out = document.getElementById(id);
  const c = out.querySelector('canvas').getBoundingClientRect();
  const o = out.getBoundingClientRect();
  return Math.abs(c.width - o.width) <= 1 && Math.abs(c.height - o.height) <= 1;
}"""


def count_drawn_pixels(locator: Locator) -> int:
    # WebGL canvases can't be read back through a 2D context, so inspect a screenshot
    image = Image.open(io.BytesIO(locator.screenshot())).convert("RGB")
    return sum(1 for r, g, b in image.getdata() if min(r, g, b) < 200)


def wait_until_drawn(page: Page, locator: Locator) -> None:
    for _ in range(50):
        if count_drawn_pixels(locator) > MIN_DRAWN_PIXELS:
            return
        page.wait_for_timeout(200)
    raise AssertionError("nglview never drew anything")


def sizes(page: Page, output_id: str) -> dict[str, list[float]]:
    return page.evaluate(SIZES_JS, output_id)


def test_nglview_renders_visibly(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    canvas = page.locator("#view canvas")
    expect(canvas).to_have_count(1, timeout=30000)
    box = canvas.bounding_box()
    assert box is not None and box["width"] > 0 and box["height"] > 0

    wait_until_drawn(page, canvas)

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_fills_fixed_height_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#view canvas")).to_have_count(1, timeout=30000)

    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="view", timeout=30000)
    wide = sizes(page, "view")
    container = page.locator("#fill_container").bounding_box()
    assert container is not None
    # The output fills the 400px-tall container (minus its 1px borders)
    assert abs(wide["out"][1] - (container["height"] - 2)) <= 1
    assert abs(wide["canvas"][1] - wide["out"][1]) <= 1

    # ... and keeps tracking the container's width when the window resizes
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(
        """(w) => document.getElementById('view').querySelector('canvas')
            .getBoundingClientRect().width < w""",
        arg=wide["canvas"][0] - 100,
        timeout=30000,
    )
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="view", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_respects_explicit_height(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#fixed canvas")).to_have_count(1, timeout=30000)

    page.wait_for_function(
        """() => document.getElementById('fixed').querySelector('canvas')
            .getBoundingClientRect().height === 250""",
        timeout=30000,
    )
    s = sizes(page, "fixed")
    assert s["out"][1] == 250
    assert s["canvas"][1] == 250
    assert abs(s["canvas"][0] - s["out"][0]) <= 1

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_with_own_height_tracks_output_width(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(local_app.url)
    expect(page.locator("#own_height_view canvas")).to_have_count(1, timeout=30000)
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="own_height_view", timeout=30000)
    wide = sizes(page, "own_height_view")
    assert wide["canvas"][1] == 250

    # The widget's own height isn't the output's, but its width still is
    page.set_viewport_size({"width": 600, "height": 900})
    page.wait_for_function(
        f"""(w) => {{
          const s = ({SIZES_JS})('own_height_view');
          return s.out[0] < w && Math.abs(s.canvas[0] - s.out[0]) <= 1;
        }}""",
        arg=wide["out"][0] - 100,
        timeout=10000,
    )
    narrow = sizes(page, "own_height_view")
    assert narrow["canvas"][1] == 250
    assert narrow["out"][1] == 250

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_rerender_with_own_height_stops_filling(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#view canvas")).to_have_count(1, timeout=30000)
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="view", timeout=30000)

    # The output filled on the first render; a re-render whose widget has its own
    # height must not be resized to the (still fillable) container
    page.click("#own_height")
    page.wait_for_function(
        """() => document.querySelector('#view .lm-Widget')?.style.height === '200px'""",
        timeout=30000,
    )
    expect(page.locator("#view canvas")).to_have_count(1, timeout=30000)
    page.wait_for_function(
        """() => document.querySelector('#view canvas')
            .getBoundingClientRect().height === 200""",
        timeout=30000,
    )
    container = page.locator("#fill_container").bounding_box()
    assert container is not None and container["height"] == 400

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_click_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#picked_atom")).to_have_text("none", timeout=30000)
    canvas = page.locator("#view canvas")
    expect(canvas).to_have_count(1)

    # The single atom is centered in the view; wait for it to be drawn first
    wait_until_drawn(page, canvas)
    canvas.click()
    expect(page.locator("#picked_atom")).to_contain_text("HOH", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_rerender_releases_old_views(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator("#view canvas")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")
    initial = wait_for_stable_view_count(page)

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(page.locator("#view canvas")).to_have_count(1, timeout=30000)

    expect(page.locator("#view > .lm-Widget")).to_have_count(1)
    assert wait_for_stable_view_count(page) == initial
    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_subclass_tracks_its_container(page: Page, local_app) -> None:
    # An app-defined NGLWidget subclass reports the app's module as its
    # widget_pkg, so the browser has to recognize it by what it inherits (its
    # inherited NGLView, i.e. the sizing hooks nglview gets). nglview measures
    # itself once on render, so only tracking a resize shows whether the hooks
    # ran.
    errors, failed_requests = collect_errors(page)
    page.set_viewport_size({"width": 900, "height": 1400})
    page.goto(local_app.url)
    expect(page.locator("#subclassed canvas")).to_have_count(1, timeout=30000)
    page.wait_for_function(CANVAS_FILLS_OUTPUT_JS, arg="subclassed", timeout=30000)
    wide = sizes(page, "subclassed")
    container = page.locator("#subclass_container").bounding_box()
    assert container is not None
    assert abs(wide["out"][1] - (container["height"] - 2)) <= 1

    page.set_viewport_size({"width": 600, "height": 1400})
    page.wait_for_function(
        f"""(w) => {{
          const s = ({SIZES_JS})('subclassed');
          return s.out[0] < w && Math.abs(s.canvas[0] - s.out[0]) <= 1;
        }}""",
        arg=wide["out"][0] - 100,
        timeout=10000,
    )
    narrow = sizes(page, "subclassed")
    assert abs(narrow["canvas"][1] - narrow["out"][1]) <= 1

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_respects_constructor_width(page: Page, local_app) -> None:
    # NGLWidget(width=...) sizes the stage itself, so the output must not widen it
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#width_view canvas")).to_have_count(1, timeout=30000)

    page.wait_for_function(
        """() => document.getElementById('width_view').querySelector('canvas')
            .getBoundingClientRect().width === 200""",
        timeout=30000,
    )
    s = sizes(page, "width_view")
    assert s["canvas"] == [200, 200]

    # ... and keeps it when the output narrows
    page.set_viewport_size({"width": 500, "height": 720})
    page.wait_for_function(
        """() => document.getElementById('width_view').getBoundingClientRect().width < 500""",
        timeout=30000,
    )
    assert sizes(page, "width_view")["canvas"] == [200, 200]

    assert_no_unexpected_errors(errors, failed_requests)


def test_nglview_child_removal_disposes_stage(page: Page, local_app) -> None:
    # A container dropping a child calls view.remove() directly, which doesn't go
    # through the output binding's teardown; the stage must still be disposed
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    expect(page.locator("#boxed canvas")).to_have_count(1, timeout=30000)

    # Spy on the stage's dispose() so the removal's effect is observable
    page.wait_for_function(
        """() => {
          const view = Array.from(window.widgetManager._liveViews).find(
            (v) => v.model && v.model.get('_view_name') === 'NGLView' &&
              document.getElementById('boxed').contains(v.el)
          );
          if (!view || !view.stage) return false;
          window.__nglDisposed = 0;
          const dispose = view.stage.dispose.bind(view.stage);
          view.stage.dispose = () => { window.__nglDisposed += 1; dispose(); };
          return true;
        }""",
        timeout=30000,
    )

    page.click("#remove_child")
    expect(page.locator("#boxed canvas")).to_have_count(0, timeout=30000)
    assert page.evaluate("() => window.__nglDisposed") == 1

    assert_no_unexpected_errors(errors, failed_requests)


def count_blue_pixels(locator: Locator) -> int:
    image = Image.open(io.BytesIO(locator.screenshot())).convert("RGB")
    return sum(
        1 for r, g, b in image.getdata() if b > 100 and b > r + 40 and b > g + 40
    )


def wait_for_blue_pixels(locator: Locator, page: Page, minimum: int = 50) -> None:
    for _ in range(50):
        try:
            if count_blue_pixels(locator) > minimum:
                return
        except Exception:
            pass
        page.wait_for_timeout(200)
    raise AssertionError("no blue (custom-scheme) pixels ever appeared")


def test_custom_color_scheme_renders_in_browser(page: Page, local_app) -> None:
    # The app registers "sw_blue" on the process-global ColormakerRegistry at
    # import time; the registry's view must render (hidden) in the browser and
    # receive the registration before the representation is created
    errors, failed_requests = collect_errors(page)
    warnings: list[str] = []
    page.on(
        "console",
        lambda msg: warnings.append(msg.text) if msg.type == "warning" else None,
    )
    page.goto(local_app.url)
    canvas = page.locator("#custom_scheme canvas")
    expect(canvas).to_have_count(1, timeout=30000)

    wait_for_blue_pixels(canvas, page)

    # In particular: NGL never fell back to parsing "sw_blue" as a color
    assert not any("Unknown color" in w for w in warnings)
    assert_no_unexpected_errors(errors, failed_requests)


def test_custom_color_scheme_reaches_a_second_session(page: Page, local_app) -> None:
    # The registry fans out to every session, and each browser renders its own
    # hidden registry view
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#custom_scheme canvas")).to_have_count(1, timeout=30000)
    wait_for_blue_pixels(page.locator("#custom_scheme canvas"), page)

    page2 = page.context.new_page()
    page2.goto(local_app.url)
    canvas2 = page2.locator("#custom_scheme canvas")
    expect(canvas2).to_have_count(1, timeout=30000)
    wait_for_blue_pixels(canvas2, page2)
    page2.close()

    assert_no_unexpected_errors(errors, failed_requests)


def test_method_call_updates_viewer_in_place(page: Page, local_app) -> None:
    # add_representation() runs on nglview's background thread; the update must
    # still reach the browser, without a re-render
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    canvas = page.locator("#view canvas")
    expect(canvas).to_have_count(1, timeout=30000)
    wait_until_drawn(page, canvas)
    assert page.locator("#render_count").inner_text() == "0"
    assert count_blue_pixels(canvas) <= 50

    page.click("#add_spacefill")

    wait_for_blue_pixels(canvas, page)
    # No re-render happened (the counter only increments via the Rerender button)
    assert page.locator("#render_count").inner_text() == "0"
    assert_no_unexpected_errors(errors, failed_requests)
