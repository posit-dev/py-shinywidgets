# A synthetic elevation raster is written to a local Cloud-Optimized GeoTIFF at
# startup; leafmap's add_raster() serves it with localtileserver, and
# shinywidgets' loopback proxy makes the tile requests work even when the app
# is deployed (see ../../localtileserver/guide.md). Needs leafmap's raster
# extra (pip install 'leafmap[raster]') plus rioxarray and scipy to generate
# the sample data: `uv run --with rioxarray,scipy shiny run 05_raster_cog.py`.
import tempfile
from pathlib import Path

import leafmap
import numpy as np
import rioxarray  # noqa: F401  (registers the .rio accessor)
import xarray as xr
from scipy.ndimage import zoom
from shiny.express import ui
from shinywidgets import render_leafmap


def make_terrain_cog(path: Path, n: int = 600) -> None:
    rng = np.random.default_rng(7)
    elev = np.zeros((n, n), dtype=np.float32)
    for octave in range(6):  # fBm: stack smoothed noise at doubling frequencies
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

ui.page_opts(title="leafmap local raster", fillable=True)


@render_leafmap
def map():
    m = leafmap.Map(center=(47.6, -122.33), zoom=12)
    # zoom_to_layer=False keeps the view above; True (the default) refits to
    # the raster's bounds, which is usually what you want for a first render
    m.add_raster(
        str(COG), colormap="terrain", layer_name="Elevation", zoom_to_layer=False
    )
    return m
