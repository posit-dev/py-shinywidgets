from __future__ import annotations

import asyncio
import json
import struct
import tempfile
from functools import partial
from pathlib import Path

from geolibre import Map
from shiny import App, reactive, render, ui
from shiny.reactive import extended_task
from shinywidgets import output_widget, reactive_read, render_geolibre


def _tiny_geotiff_bytes() -> bytes:
    """A minimal valid single-band GeoTIFF (EPSG:4326) covering the CONUS.

    64x64 uint8 grayscale; raster (0,0) at (-125, 50), 0.5 degree pixels.
    Written by hand so the test suite doesn't need rasterio/GDAL.
    """
    width = height = 64
    pixels = bytes((x * 4 + y) % 256 for y in range(height) for x in range(width))
    scale = struct.pack("<3d", 0.5, 0.5, 0.0)
    tiepoint = struct.pack("<6d", 0.0, 0.0, 0.0, -125.0, 50.0, 0.0)
    # GeoKeyDirectory: version 1.1.0, 2 keys:
    #   GTModelTypeGeoKey=2 (geographic), GeographicTypeGeoKey=4326 (EPSG:4326)
    geokeys = struct.pack("<12H", 1, 1, 0, 2, 1024, 0, 1, 2, 2048, 0, 1, 4326)

    n_entries = 13
    data_offset = 8 + 2 + n_entries * 12 + 4
    scale_off = data_offset
    tie_off = scale_off + len(scale)
    keys_off = tie_off + len(tiepoint)
    pixels_off = keys_off + len(geokeys)

    SHORT, LONG, DOUBLE = 3, 4, 12

    def entry(tag: int, type_: int, count: int, value: int) -> bytes:
        if type_ == SHORT and count == 1:
            return (
                struct.pack("<HHI", tag, type_, count)
                + struct.pack("<H", value)
                + b"\x00\x00"
            )
        return struct.pack("<HHII", tag, type_, count, value)

    ifd = b"".join(
        [
            struct.pack("<H", n_entries),
            entry(256, LONG, 1, width),  # ImageWidth
            entry(257, LONG, 1, height),  # ImageLength
            entry(258, SHORT, 1, 8),  # BitsPerSample
            entry(259, SHORT, 1, 1),  # Compression: none
            entry(262, SHORT, 1, 1),  # PhotometricInterpretation: BlackIsZero
            entry(273, LONG, 1, pixels_off),  # StripOffsets
            entry(277, SHORT, 1, 1),  # SamplesPerPixel
            entry(278, LONG, 1, height),  # RowsPerStrip
            entry(279, LONG, 1, len(pixels)),  # StripByteCounts
            entry(284, SHORT, 1, 1),  # PlanarConfiguration: chunky
            entry(33550, DOUBLE, 3, scale_off),  # ModelPixelScaleTag
            entry(33922, DOUBLE, 6, tie_off),  # ModelTiepointTag
            entry(34735, SHORT, 12, keys_off),  # GeoKeyDirectoryTag
            struct.pack("<I", 0),  # next IFD
        ]
    )
    return (
        struct.pack("<2sHI", b"II", 42, 8) + ifd + scale + tiepoint + geokeys + pixels
    )


# A GeoTIFF on the server's disk: its layer is served from geolibre's loopback
# server, which the browser can only reach through shinywidgets' /proxy/{port}/
# mount (see test_geolibre_local_cog_via_proxy).
LOCAL_TIF = Path(tempfile.gettempdir()) / "shinywidgets-test-tiny.tif"
LOCAL_TIF.write_bytes(_tiny_geotiff_bytes())

app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(output_widget("map")),
        ui.card(output_widget("map_fixed")),
        ui.card(output_widget("map_output_height", height="400px")),
    ),
    # Keep the controls to a fixed height so they can't wrap and shrink the
    # filling cards above (test_geolibre_fills_and_respects_explicit_heights)
    ui.div(
        ui.input_action_button("rerender", "Rerender"),
        ui.input_action_button("add_local", "Add local COG"),
        ui.input_action_button("fly", "Fly to SF"),
        ui.input_action_button("fly_async", "Fly to SF (async)"),
        ui.output_text("render_count", inline=True),
        ui.output_text("clicked", inline=True),
        ui.output_text("view", inline=True),
        ui.output_text("flown", inline=True),
        ui.output_text("flown_async", inline=True),
        style="display: flex; gap: 0.5rem; align-items: center; height: 45px; overflow: hidden;",
    ),
)


def server(input, output, session):
    counter = reactive.value(0)
    click = reactive.value(None)
    flown_center = reactive.value("")
    flown_async_center = reactive.value("")

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_geolibre
    def map():
        input.rerender()
        m = Map(center=(-98.5, 39.8), zoom=4)
        m.on_click(lambda e: click.set(e))
        return m

    @render_geolibre
    def map_fixed():
        return Map(center=(-98.5, 39.8), zoom=4, height="500px")

    @render_geolibre
    def map_output_height():
        return Map(center=(-98.5, 39.8), zoom=4)

    # Add a layer backed by a file on the server's disk (its URL points at
    # geolibre's loopback server)
    @reactive.effect
    @reactive.event(input.add_local)
    def _():
        map.widget.add_cog(LOCAL_TIF, name="Local COG")

    # Blocking command methods (fly_to(), get_center(), ...) must run off
    # Shiny's event-loop thread, so the reply can be delivered while they
    # wait. extended_task + run_in_executor puts them on a worker thread
    # (requires geolibre >= 3.5.2, which sleep-polls for the reply).
    @extended_task
    async def fly_to_sf():
        loop = asyncio.get_running_loop()
        # fly_to() only waits for the app's acknowledgement (sent when the
        # animation starts), not for the camera animation to finish, so give
        # it a beat before get_center(). An upstream `wait=` option (ack at
        # animation end, or final view state in the ack payload) would make
        # this sleep unnecessary.
        await loop.run_in_executor(
            None, partial(map.widget.fly_to, -122.4, 37.8, duration=1000)
        )
        await asyncio.sleep(2)
        center = await loop.run_in_executor(None, map.widget.get_center)
        flown_center.set(json.dumps(center))

    @reactive.effect
    @reactive.event(input.fly)
    def _():
        fly_to_sf.invoke()

    # geolibre releases containing opengeos/GeoLibre#3273 (pending; the first
    # after 3.5.2) add *_async() variants that await the reply instead of
    # blocking a thread, so they run directly on Shiny's event loop inside an
    # extended_task -- no run_in_executor.
    @extended_task
    async def fly_to_sf_async():
        # Same ack-at-animation-start caveat as fly_to() above: let the
        # animation settle before querying the center.
        await map.widget.fly_to_async(-122.4, 37.8, duration=1000)
        await asyncio.sleep(2)
        center = await map.widget.get_center_async()
        flown_async_center.set(json.dumps(center))

    @reactive.effect
    @reactive.event(input.fly_async)
    def _():
        fly_to_sf_async.invoke()

    @render.text
    def flown():
        return flown_center.get()

    @render.text
    def flown_async():
        return flown_async_center.get()

    @render.text
    def clicked():
        e = click.get()
        return "" if e is None else json.dumps(e["lngLat"])

    @render.text
    def view():
        project = reactive_read(map.widget, "project")
        mv = project.get("mapView", {})
        return json.dumps({"center": mv.get("center"), "zoom": mv.get("zoom")})


app = App(app_ui, server)
