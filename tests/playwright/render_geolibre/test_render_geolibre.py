from __future__ import annotations

import json

import pytest
from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# The widget embeds the bundled GeoLibre app, which fetches its basemap style
# and tiles from remote hosts; tolerate failed requests to those (e.g., tile
# 404s), along with the "Failed to load resource" console errors they produce.
ALLOWED_REQUEST_FAILURES = ("openfreemap", "openstreetmap", "arcgis")

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


def test_geolibre_local_cog_via_proxy(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    wait_for_app(page, "map")

    # The embedded app loads through shinywidgets' /proxy/{port}/ mount (the
    # jupyter-server-proxy equivalent geolibre's front-end probes for first,
    # and the only mode in which it rewrites loopback local-file URLs onto a
    # same-origin base)
    src = page.locator("#map iframe").get_attribute("src")
    assert src is not None and "/proxy/" in src

    # A layer backed by a file on the server's disk is fetched by the browser
    # through the proxy (same-origin), not from geolibre's loopback address
    with page.expect_response(
        lambda r: "/_geolibre_local/" in r.url, timeout=LOAD_TIMEOUT
    ) as resp_info:
        page.click("#add_local")
    resp = resp_info.value
    assert resp.ok
    # The request goes to the Shiny app's own origin (via the proxy mount),
    # not to geolibre's loopback server (a different port on the same host)
    assert resp.url.startswith(local_app.url)
    assert "/proxy/" in resp.url

    check_errors(errors, failed_requests)


def test_geolibre_blocking_methods_from_extended_task(page: Page, local_app) -> None:
    # geolibre's blocking command methods (fly_to(), get_center(), ...) wait
    # for a reply from the app, so they can only run off Shiny's event-loop
    # thread -- and only with geolibre >= 3.5.2 (enforced by the geolibre
    # extra), which sleep-polls for the reply instead of pumping a Jupyter
    # kernel (opengeos/GeoLibre#3266).
    pytest.importorskip("geolibre")

    page.goto(local_app.url)
    wait_for_app(page, "map")

    # The app calls fly_to(-122.4, 37.8) then get_center(), both via
    # run_in_executor inside an extended_task (see app.py). Compare floats
    # with tolerance: the reported center carries fp jitter either side of
    # the target (e.g. -122.4000000000043 or -122.3999999999952).
    page.click("#fly")
    expect(page.locator("#flown")).not_to_have_text("", timeout=LOAD_TIMEOUT)
    center = json.loads(page.locator("#flown").inner_text())
    assert center[0] == pytest.approx(-122.4, abs=1e-6)
    assert center[1] == pytest.approx(37.8, abs=1e-6)


def test_geolibre_async_methods_from_extended_task(page: Page, local_app) -> None:
    # geolibre's *_async() command methods (fly_to_async(), get_center_async(),
    # ...) await the app's reply instead of blocking a thread, so they run
    # directly on Shiny's event loop inside an extended_task -- no
    # run_in_executor. They require a geolibre release containing
    # opengeos/GeoLibre#3273 (pending; the first after 3.5.2), so skip (rather
    # than fail) until then.
    geolibre = pytest.importorskip("geolibre")
    if not hasattr(geolibre.Map, "fly_to_async"):
        pytest.skip(
            "geolibre without the async command methods "
            "(needs a release containing opengeos/GeoLibre#3273)"
        )

    page.goto(local_app.url)
    wait_for_app(page, "map")

    # Same flow and float-tolerance rationale as
    # test_geolibre_blocking_methods_from_extended_task, but via
    # fly_to_async()/get_center_async() awaited directly in the extended_task
    # (see app.py).
    page.click("#fly_async")
    expect(page.locator("#flown_async")).not_to_have_text("", timeout=LOAD_TIMEOUT)
    center = json.loads(page.locator("#flown_async").inner_text())
    assert center[0] == pytest.approx(-122.4, abs=1e-6)
    assert center[1] == pytest.approx(37.8, abs=1e-6)


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
