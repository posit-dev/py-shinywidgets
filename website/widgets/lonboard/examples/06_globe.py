import geopandas as gpd
from lonboard import Map, ScatterplotLayer
from lonboard._map import GlobeView
from lonboard.basemap import MaplibreBasemap
from shiny.express import ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"


@render_lonboard
def map():
    cities = ScatterplotLayer.from_geopandas(
        gpd.read_file(CITIES_URL), get_fill_color=[255, 140, 0], radius_min_pixels=3
    )
    # Same layer, different view: GlobeView needs an interleaved basemap, and
    # lonboard raises a clear error if you forget it.
    return Map(cities, view=GlobeView(), basemap=MaplibreBasemap(mode="interleaved"))
