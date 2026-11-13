import geoarrow.rust.core as gr
import numpy as np
from arro3.core import Table
from lonboard import ScatterplotLayer
from shiny.express import ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)


# lonboard's native format is GeoArrow, not just GeoDataFrame: here a table is
# built directly from a GeoArrow point array, with no geopandas/shapely
# involved at all. This is the fastest path for data that's already Arrow
# (e.g., read from a GeoParquet file or a DuckDB spatial query).
@render_lonboard
def map():
    rng = np.random.default_rng(0)
    lon = rng.uniform(-74.05, -73.95, 2000)
    lat = rng.uniform(40.68, 40.78, 2000)
    points = gr.points((lon, lat), crs="EPSG:4326")
    table = Table.from_arrays([points], names=["geometry"])
    return ScatterplotLayer(table=table, get_fill_color=[0, 150, 255], radius_min_pixels=2)
