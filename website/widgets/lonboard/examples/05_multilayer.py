import geopandas as gpd
from lonboard import Map, PolygonLayer, ScatterplotLayer
from lonboard.basemap import CartoStyle, MaplibreBasemap
from shiny.express import ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

COUNTRIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"


@render_lonboard
def map():
    countries = PolygonLayer.from_geopandas(
        gpd.read_file(COUNTRIES_URL),
        get_fill_color=[40, 40, 40],
        get_line_color=[90, 90, 90],
        opacity=0.6,
    )
    cities = ScatterplotLayer.from_geopandas(
        gpd.read_file(CITIES_URL),
        get_fill_color=[255, 210, 0],
        radius_min_pixels=2,
        pickable=True,
    )
    # A Map holds a list of layers; order determines draw order (last on top)
    return Map([countries, cities], basemap=MaplibreBasemap(style=CartoStyle.DarkMatter))
