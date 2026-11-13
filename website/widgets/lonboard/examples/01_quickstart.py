import geopandas as gpd
from shiny.express import ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

# ~240 populated places from Natural Earth (110m scale), with longitude/
# latitude and population columns.
CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"


@render_lonboard
def map():
    cities = gpd.read_file(CITIES_URL)
    return cities  # lonboard.viz() picks a ScatterplotLayer and fits the view
