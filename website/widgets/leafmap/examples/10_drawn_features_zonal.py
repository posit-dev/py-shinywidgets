# Needs leafmap's raster extra (pip install 'leafmap[raster]') plus rioxarray,
# scipy, and shapely for the synthetic raster and the AOI clip: `uv run --with
# rioxarray,scipy,shapely,plotly shiny run 10_drawn_features_zonal.py`.
import tempfile
from pathlib import Path

import leafmap
import numpy as np
import plotly.express as px
import rioxarray  # noqa: F401  (registers the .rio accessor)
import shapely.geometry
import xarray as xr
from scipy.ndimage import zoom
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import render_leafmap, render_plotly


def make_terrain_cog(path: Path, n: int = 600) -> None:
    rng = np.random.default_rng(7)
    elev = np.zeros((n, n), dtype=np.float32)
    for octave in range(6):
        k = 3 * 2**octave
        elev += zoom(rng.normal(0, 1, (k, k)).astype(np.float32), n / k, order=3)[
            :n, :n
        ] * (400 / 2**octave)
    elev = np.clip(elev - elev.min(), 0, None)
    ys = np.linspace(47.75, 47.45, n)
    xs = np.linspace(-122.5, -122.15, n)
    da = xr.DataArray(elev, dims=("y", "x"), coords={"y": ys, "x": xs})
    da.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
    da.rio.write_crs("EPSG:4326", inplace=True)
    da.rio.to_raster(path, driver="COG", compress="deflate")


COG = Path(tempfile.gettempdir()) / "shinywidgets_leafmap_terrain.tif"
if not COG.exists():
    make_terrain_cog(COG)
ELEVATION = rioxarray.open_rasterio(COG).squeeze("band", drop=True)

ui.page_opts(title="Draw an AOI, see zonal stats", fillable=True)

with ui.layout_columns(col_widths=(8, 4)):

    @render_leafmap
    def map():
        m = leafmap.Map(center=(47.6, -122.33), zoom=12)
        m.add_raster(
            str(COG), colormap="terrain", layer_name="Elevation", zoom_to_layer=False
        )
        return m

    with ui.card():
        ui.card_header("Elevation inside the drawn area")

        @reactive.calc
        def clipped():
            # drawn_features() is a list of GeoJSON Features: the AOI to clip to
            features = map.drawn_features()
            req(features)
            geom = shapely.geometry.shape(features[-1]["geometry"])
            return ELEVATION.rio.clip([geom.__geo_interface__], "EPSG:4326")

        @render.express
        def stats():
            data = clipped()
            ui.div(f"mean: {float(data.mean()):.0f} m")
            ui.div(f"min: {float(data.min()):.0f} m -- max: {float(data.max()):.0f} m")
            ui.div(f"{data.size} pixels in the drawn area")

        @render_plotly
        def hist():
            return px.histogram(
                clipped().values.ravel(), nbins=30, labels={"value": "elevation (m)"}
            )
