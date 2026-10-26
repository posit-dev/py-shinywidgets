from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The widget embeds the bundled GeoLibre app, which fetches its basemap style
# and tiles from remote hosts; tolerate failed requests to those (e.g., tile
# 404s), along with the "Failed to load resource" console errors they produce.
# The /proxy/{port}/ 404 is geolibre's front-end probing for jupyter-server-proxy
# before falling back to the bundle shinywidgets serves at /geolibre/app/ (by
# design; see geolibre_app_mount() in _dependencies.py).
ALLOWED_REQUEST_FAILURES = ("openfreemap", "openstreetmap", "arcgis", "/proxy/")

# geolibre shadows ipywidgets' `layout` trait with its own (the app chrome
# layout: "embed"/"full"/"maponly"), so the client's DOMWidgetView hands a
# plain string to create_child_view() instead of a Layout model. That surfaces
# as a "Cannot read properties of undefined (reading 'then')" uncaught error
# per render. It's cosmetic (the map renders and functions), and needs an
# upstream fix (renaming the trait), so tolerate it here.
ALLOWED_ERRORS = ("Cannot read properties of undefined (reading 'then')",)

# The embedded app takes a while to load (a multi-chunk SPA from the
# localhost server), so give expectations a long timeout
LOAD_TIMEOUT = 60000


def map_frame(page: Page, output_id: str):
    return page.frame_locator(f"#{output_id} iframe")


def check_errors(errors: list[str], failed_requests: list[str]) -> None:
    errors = [
        e
        for e in errors
        if not (
            any(host in e for host in ALLOWED_REQUEST_FAILURES)
            or any(allowed in e for allowed in ALLOWED_ERRORS)
            or "Failed to load resource" in e
        )
    ]
    assert_no_unexpected_errors(
        errors, failed_requests, allowed_404s=ALLOWED_REQUEST_FAILURES
    )


def test_geolibre_renders(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    for id in ("map", "map_fixed", "map_output_height"):
        expect(page.locator(f"#{id} iframe")).to_be_visible(timeout=LOAD_TIMEOUT)
        # the embedded app's own canvas (the map) shows up once it loads
        expect(map_frame(page, id).locator("canvas").first).to_be_visible(
            timeout=LOAD_TIMEOUT
        )

    check_errors(errors, failed_requests)


def test_geolibre_fills_and_respects_explicit_heights(page: Page, local_app) -> None:
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(local_app.url)

    for id in ("map", "map_fixed", "map_output_height"):
        expect(map_frame(page, id).locator("canvas").first).to_be_visible(
            timeout=LOAD_TIMEOUT
        )

    def iframe_height(id: str) -> float:
        return page.evaluate(
            "(id) => document.querySelector(`#${id} iframe`).getBoundingClientRect().height",
            id,
        )

    # The default-height map fills its (filling) card; the explicit-height one
    # keeps its own height; an output height sizes the filling map
    assert iframe_height("map") > 600
    assert iframe_height("map_fixed") == 500
    assert abs(iframe_height("map_output_height") - 400) < 20


def wait_for_app(page: Page, output_id: str) -> None:
    """Wait for the embedded app's chrome (not just its canvas) to appear.

    The app only answers clicks once its UI has booted, which is several
    seconds after the canvas first shows.
    """
    frame = map_frame(page, output_id)
    expect(frame.locator("canvas").first).to_be_visible(timeout=LOAD_TIMEOUT)
    expect(frame.get_by_text("Zoom:", exact=False).first).to_be_visible(
        timeout=LOAD_TIMEOUT
    )


def test_geolibre_interaction(page: Page, local_app) -> None:
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(local_app.url)
    wait_for_app(page, "map")
    canvas = map_frame(page, "map").locator("canvas").first
    expect(canvas).to_be_visible(timeout=LOAD_TIMEOUT)

    # Clicking the embedded map fires geolibre's on_click event
    canvas.click(position={"x": 400, "y": 250}, timeout=LOAD_TIMEOUT)
    expect(page.locator("#clicked")).not_to_have_text("", timeout=LOAD_TIMEOUT)

    # Panning the map syncs the project (and its mapView) back to Python
    expect(page.locator("#view")).to_contain_text("-98.5", timeout=LOAD_TIMEOUT)
    box = canvas.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + 400, box["y"] + 250)
    page.mouse.down()
    page.mouse.move(box["x"] + 550, box["y"] + 350, steps=10)
    page.mouse.up()
    expect(page.locator("#view")).not_to_contain_text("-98.5", timeout=LOAD_TIMEOUT)


def test_geolibre_rerender(page: Page, local_app) -> None:
    page.goto(local_app.url)
    expect(map_frame(page, "map").locator("canvas").first).to_be_visible(
        timeout=LOAD_TIMEOUT
    )
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 3):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        expect(map_frame(page, "map").locator("canvas").first).to_be_visible(
            timeout=LOAD_TIMEOUT
        )
        # the previous render's iframe is replaced, not leaked
        expect(page.locator("#map iframe")).to_have_count(1)
