# "Synthetic Sierra" — xarray -> COG -> localtileserver -> ipyleaflet in Shiny.
#
# Run:  uv run --with localtileserver,rioxarray,scipy shiny run app.py
#   (or: pip install -r requirements.txt && shiny run app.py)
#
# A synthetic xarray elevation dataset is written to a Cloud-Optimized GeoTIFF at
# startup, then served as slippy-map tiles by localtileserver's in-process tile
# server. shinywidgets automatically mounts a loopback reverse proxy for that
# server and rewrites the layer's tile URLs onto it, so the app works
# identically when deployed to a remote server -- not just when the browser
# shares localhost. The proxy only forwards tile requests for rasters the app
# itself registered (localtileserver's `filename` API is otherwise
# unauthenticated); set SHINYWIDGETS_LOOPBACK_PROXY_DISABLE=1 to opt out.
import tempfile
from pathlib import Path

import numpy as np
import rioxarray  # noqa: F401  (registers the .rio accessor)
import xarray as xr
from localtileserver import TileClient, get_leaflet_tile_layer
from scipy.ndimage import zoom
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipyleaflet


def make_terrain_cog(path: Path, n: int = 1600) -> None:
    """Fractal terrain as a 3-band COG (elevation, slope, moisture)."""
    rng = np.random.default_rng(7)
    elev = np.zeros((n, n), dtype=np.float32)
    for octave in range(7):  # fBm: stack smoothed noise at doubling frequencies
        k = 3 * 2**octave
        elev += zoom(rng.normal(0, 1, (k, k)).astype(np.float32), n / k, order=3)[:n, :n] * (
            900 / 2**octave
        )
    elev = np.clip(elev - elev.min(), 0, None)
    gy, gx = np.gradient(elev)
    slope = np.hypot(gx, gy).astype(np.float32)
    moisture = (np.clip(elev / elev.max(), 0, 1) ** 2).astype(np.float32)  # snowline proxy
    ys = np.linspace(38.4, 37.4, n)
    xs = np.linspace(-122.6, -121.6, n)
    bands = []
    for i, arr in enumerate((elev, slope, moisture)):
        da = xr.DataArray(arr, dims=("y", "x"), coords={"y": ys, "x": xs})
        da.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
        da.rio.write_crs("EPSG:4326", inplace=True)
        bands.append(da)
    xr.concat(bands, dim="band").transpose("band", "y", "x").rio.to_raster(
        path, driver="COG", compress="deflate"
    )


COG = Path(tempfile.gettempdir()) / "shinywidgets_gallery_terrain.tif"
if not COG.exists():
    make_terrain_cog(COG)

# Create the TileClient at module scope, never inside a render (the first open
# takes ~4s; later layers on the same server are fast)
client = TileClient(COG)
STATS = client.statistics()
ELEV_MAX = float(np.ceil(STATS["b1"]["max"] / 100) * 100)
SLOPE_MAX = float(np.ceil(STATS["b2"]["max"]))

# style name -> (get_tile_url kwargs, natural vmax for the rescale slider)
STYLES = {
    "Elevation (b1)": (dict(indexes=[1], colormap="terrain"), ELEV_MAX),
    "Slope (b2)": (dict(indexes=[2], colormap="magma"), SLOPE_MAX),
    "Snowline proxy (b3)": (dict(indexes=[3], colormap="blues"), 1.0),
    "Ruggedness (b2/b1)": (dict(expression="b2/b1", colormap="rdylbu"), 0.2),
}

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("style", "Layer", list(STYLES)),
            ui.input_slider("range", "Value range", 0, 1, value=[0, 0.8], step=0.01),
            ui.input_slider("opacity", "Opacity", 0, 1, value=0.85, step=0.05),
            ui.output_code("mapstate"),
            ui.markdown(
                "**xarray -> COG -> tiles.** Styling is encoded in the tile URL, "
                "so these controls only flip a trait -- no re-render, no data re-send."
            ),
        ),
        ui.card(
            ui.card_header("Synthetic Sierra — served by localtileserver"),
            output_widget("map"),
            full_screen=True,
        ),
    ),
)


def server(input, output, session):
    @render_ipyleaflet
    def map():
        layer = get_leaflet_tile_layer(client, indexes=[1], colormap="terrain")
        m = client.get_leaflet_map()
        m.zoom = 9
        m.add(layer)
        return m

    @reactive.effect
    def _():
        layer = map.widget.layers[1]
        style, vmax = STYLES[input.style()]
        # get_tile_url(client=True) URLs are routed through the loopback proxy
        # automatically, so restyling works locally and deployed
        layer.url = client.get_tile_url(
            **style, vmin=input.range()[0] * vmax, vmax=input.range()[1] * vmax, client=True
        )
        layer.opacity = input.opacity()

    @render.code
    def mapstate():
        c = reactive_read(map.widget, "center")
        z = reactive_read(map.widget, "zoom")
        return f"center=({c[0]:.2f}, {c[1]:.2f}) zoom={z:.1f}"


app = App(app_ui, server)
