from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The viewer loads its JavaScript from esm.sh and its sky imagery (HiPS tiles)
# from CDS servers; tolerate failed requests to those (e.g., tile 404s at
# extreme zooms), along with the "Failed to load resource" console errors they
# produce (see assert_no_unexpected_errors)
ALLOWED_REQUEST_FAILURES = ("esm.sh", "alasky", "cds.unistra.fr", "hips")

MEASURE_JS = """(id) => {
  const box = (el) => {
    const b = el.getBoundingClientRect();
    return {width: b.width, height: b.height, bottom: b.bottom};
  };
  const out = document.getElementById(id);
  const viewer = out.querySelector('.aladin-widget');
  return {out: box(out), viewer: viewer ? box(viewer) : null};
}"""


def measure(page: Page, id: str) -> dict:
    expect(page.locator(f"#{id} .aladin-widget canvas").first).to_be_visible(
        timeout=30000
    )
    return page.evaluate(MEASURE_JS, id)


def assert_fills(page: Page, id: str) -> None:
    m = measure(page, id)
    out, viewer = m["out"], m["viewer"]
    assert out["height"] > 200, m
    assert abs(viewer["width"] - out["width"]) <= 1, m
    assert abs(viewer["bottom"] - out["bottom"]) <= 1, m
    assert abs(viewer["height"] - out["height"]) <= 1, m


def check_errors(errors: list[str], failed_requests: list[str]) -> None:
    # Tile/property fetches blocked by CORS (e.g. CDS's DSS2/color survey
    # redirecting to irsa.ipac.caltech.edu, which sends no
    # Access-Control-Allow-Origin) surface as "Access to fetch ..." console
    # errors, and the blocked fetch itself as a bare "Failed to load
    # resource" console error with no matching requestfailed event -- neither
    # is visible to assert_no_unexpected_errors' failed_requests matching.
    # They're environmental and outside the widget's control, so tolerate
    # them for the same hosts.
    errors = [
        e
        for e in errors
        if not (
            any(host in e for host in ALLOWED_REQUEST_FAILURES)
            or "Failed to load resource" in e
        )
    ]
    assert_no_unexpected_errors(
        errors, failed_requests, allowed_404s=ALLOWED_REQUEST_FAILURES
    )


def test_ipyaladin_renders(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    for id in ("sky", "sky_fixed", "sky_output_height", "sky_unfillable"):
        expect(page.locator(f"#{id} .aladin-widget canvas").first).to_be_visible(
            timeout=30000
        )

    check_errors(errors, failed_requests)


def test_ipyaladin_fills_and_respects_explicit_heights(page: Page, local_app) -> None:
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(local_app.url)

    assert_fills(page, "sky")
    tall = measure(page, "sky")["viewer"]["height"]

    # ... and tracks its container when the window resizes
    page.set_viewport_size({"width": 1400, "height": 600})
    page.wait_for_function(
        f"() => document.querySelector('#sky .aladin-widget').getBoundingClientRect().height < {tall - 100}"
    )
    assert_fills(page, "sky")

    # Aladin(height=250) is respected (rather than growing to fill its card)
    fixed = measure(page, "sky_fixed")
    assert abs(fixed["viewer"]["height"] - 250) <= 1, fixed
    assert fixed["out"]["height"] >= 250, fixed

    # output_widget(height="300px") is respected
    out_height = measure(page, "sky_output_height")
    assert abs(out_height["out"]["height"] - 300) <= 1, out_height
    assert abs(out_height["viewer"]["height"] - 300) <= 1, out_height

    # An output with no definite height leaves the viewer at its default 400px
    unfillable = measure(page, "sky_unfillable")
    assert abs(unfillable["viewer"]["height"] - 400) <= 1, unfillable


def test_ipyaladin_pan_zoom_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    canvas = page.locator("#sky .aladin-widget canvas").first
    expect(canvas).to_be_visible(timeout=30000)
    # aladin-lite re-fits the field of view once its tiles load, so just wait
    # for a settled (non-empty) initial readout
    expect(page.locator("#fov")).not_to_have_text("", timeout=10000)
    initial_target = page.locator("#target").inner_text()
    initial_fov = page.locator("#fov").inner_text()
    assert initial_target

    # Drag the sky: the new center should sync back to Python (via the _target
    # trait and reactive_read)
    box = canvas.bounding_box()
    assert box is not None
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 80, cy + 40, steps=10)
    page.mouse.up()
    expect(page.locator("#target")).not_to_have_text(initial_target, timeout=10000)

    # Zooming with the mouse wheel syncs the field of view back (_fov)
    page.mouse.move(cx, cy)
    page.mouse.wheel(0, -240)
    expect(page.locator("#fov")).not_to_have_text(initial_fov, timeout=10000)

    check_errors(errors, failed_requests)


def test_ipyaladin_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#sky .aladin-widget")).to_have_count(1, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    # Re-rendering replaces the widget, but the old view must be disposed
    # (i.e., no accumulation of viewers)
    expect(page.locator("#sky .aladin-widget")).to_have_count(1)

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    check_errors(errors, failed_requests)
