import geopandas as gpd
import numpy as np
import pyarrow as pa
from lonboard import ArcLayer, Map
from lonboard.view_state import MapViewState
from shiny.express import ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"
HUB = "London"
DESTINATIONS = ["New York", "Dubai", "Singapore", "Johannesburg", "Sydney", "Lima"]


@render_lonboard
def map():
    cities = gpd.read_file(CITIES_URL).set_index("NAME")
    hub_lon, hub_lat = cities.loc[HUB, ["LONGITUDE", "LATITUDE"]]
    dest = cities.loc[DESTINATIONS]
    n = len(dest)

    # ArcLayer has no geometry column of its own: pass source/target
    # coordinates as plain float64 arrays, with a dummy table for the row
    # count. Without geometry, lonboard can't auto-fit the view, so set one.
    layer = ArcLayer(
        table=pa.table({"name": dest.index.tolist()}),
        get_source_position=np.column_stack(
            [np.full(n, hub_lon), np.full(n, hub_lat)]
        ),
        get_target_position=dest[["LONGITUDE", "LATITUDE"]].to_numpy(dtype="float64"),
        get_source_color=[0, 200, 255],
        get_target_color=[255, 80, 80],
        get_width=3,
    )
    return Map(layer, view_state=MapViewState(longitude=10, latitude=20, zoom=0.8))
