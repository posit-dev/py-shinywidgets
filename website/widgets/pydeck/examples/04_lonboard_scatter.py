import geopandas as gpd
import pandas as pd
import requests
from lonboard import Map, ScatterplotLayer
from shiny.express import ui
from shinywidgets import render_lonboard

BIKE_RACKS = requests.get(
    "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-bike-parking.json"
).json()
df = pd.DataFrame(BIKE_RACKS)
LNG = df["COORDINATES"].str[0]
LAT = df["COORDINATES"].str[1]
RACKS = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(LNG, LAT), crs="EPSG:4326")

ui.page_opts(fillable=True)

with ui.card(full_screen=True):

    @render_lonboard
    def bike_racks():
        return Map(
            ScatterplotLayer.from_geopandas(
                RACKS,
                get_radius=RACKS["SPACES"],
                radius_scale=6,
                radius_min_pixels=1,
                get_fill_color=[255, 140, 0],
                pickable=True,
            )
        )
