# AOI workbench -- draw one or more areas of interest on a multi-band raster and
# compare zonal stats across them, live, with no server round trip beyond the
# drawn_features() accessor.
# showcase | ~150 lines
# Run (from this directory):
#   uv run --with leafmap --with rioxarray --with localtileserver shiny run app.py
# Data: a synthetic terrain raster (elevation, slope, moisture) generated at startup
import tempfile
from pathlib import Path

import leafmap
import leafmap.common
import numpy as np
import pandas as pd
import plotly.express as px
import rioxarray  # noqa: F401  (registers the .rio accessor)
import shapely.geometry
import xarray as xr
from scipy.ndimage import zoom
from shiny import reactive, req
from shiny.express import input, render, ui
from shinywidgets import render_leafmap, render_plotly

BANDS = {"Elevation": 1, "Slope": 2, "Moisture": 3}
CMAPS = {"Elevation": "terrain", "Slope": "magma", "Moisture": "blues"}


def make_terrain_cog(path: Path, n: int = 500) -> None:
    rng = np.random.default_rng(11)
    elev = np.zeros((n, n), dtype=np.float32)
    for octave in range(6):  # fBm: stack smoothed noise at doubling frequencies
        k = 3 * 2**octave
        elev += zoom(rng.normal(0, 1, (k, k)).astype(np.float32), n / k, order=3)[
            :n, :n
        ] * (350 / 2**octave)
    elev = np.clip(elev - elev.min(), 0, None)
    gy, gx = np.gradient(elev)
    slope = np.hypot(gx, gy).astype(np.float32)
    moisture = (1 - np.clip(elev / elev.max(), 0, 1)) ** 2  # wetter in the lowlands
    ys = np.linspace(46.95, 46.65, n)
    xs = np.linspace(-121.85, -121.5, n)  # Mt. Rainier-ish bounding box
    bands = []
    for arr in (elev, slope, moisture.astype(np.float32)):
        da = xr.DataArray(arr, dims=("y", "x"), coords={"y": ys, "x": xs})
        da.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
        da.rio.write_crs("EPSG:4326", inplace=True)
        bands.append(da)
    xr.concat(bands, dim="band").transpose("band", "y", "x").rio.to_raster(
        path, driver="COG", compress="deflate"
    )


COG = Path(tempfile.gettempdir()) / "shinywidgets_leafmap_showcase_terrain.tif"
if not COG.exists():
    make_terrain_cog(COG)
RASTER = rioxarray.open_rasterio(COG)  # (band, y, x), one DataArray per band

ui.page_opts(title="AOI workbench", fillable=True)

with ui.sidebar():
    ui.input_radio_buttons("band", "Layer", list(BANDS), selected="Elevation")
    ui.markdown(
        "Draw one or more polygons on the map (the pentagon or rectangle tool). "
        "Each one gets a row below, computed from the layer currently shown."
    )

with ui.layout_columns(col_widths=(7, 5)):

    @render_leafmap
    def map():
        m = leafmap.Map(center=(46.8, -121.7), zoom=11)
        band = input.band()
        colors = leafmap.common.get_palette_colors(CMAPS[band], n_class=8, hashtag=True)
        m.add_raster(
            str(COG),
            indexes=[BANDS[band]],
            colormap=CMAPS[band],
            layer_name=band,
            zoom_to_layer=False,
        )
        data = RASTER.sel(band=BANDS[band])
        m.add_colorbar(
            colors,
            vmin=round(float(data.min()), 1),
            vmax=round(float(data.max()), 1),
            caption=band,
        )
        return m

    @reactive.calc
    def aoi_stats():
        features = map.drawn_features()
        req(features)
        band_data = RASTER.sel(band=BANDS[input.band()])
        rows = []
        for i, feat in enumerate(features):
            geom = shapely.geometry.shape(feat["geometry"])
            clipped = band_data.rio.clip([geom.__geo_interface__], "EPSG:4326")
            rows.append(
                {
                    "aoi": i + 1,
                    "mean": float(clipped.mean()),
                    "min": float(clipped.min()),
                    "max": float(clipped.max()),
                    "pixels": clipped.size,
                }
            )
        return pd.DataFrame(rows)

    # One card (not two): layout_columns() recycles col_widths across its
    # *top-level* children, so a second top-level card here would reflow the
    # whole grid. Giving the table a fixed height (rather than letting it
    # fill) is also what lets the chart below it claim the rest of the card --
    # two fill-hungry outputs stacked with no height split between them leaves
    # the second with nothing to measure, so it never reveals itself.
    with ui.card():
        ui.card_header("Zonal stats per drawn AOI")

        @render.data_frame
        def stats_table():
            return render.DataGrid(aoi_stats().round(1), height="200px")

        @render_plotly
        def stats_chart():
            df = aoi_stats()
            return px.bar(
                df, x="aoi", y="mean", title=f"Mean {input.band().lower()} by AOI"
            )
