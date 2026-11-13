import geopandas as gpd
from lonboard import ScatterplotLayer
from shiny.express import render, ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"


# view_state() debounces by default (0.25 s). render_lonboard's rate_policy/
# rate_delay kwargs now adjust that default too, not just reactive_read() on
# the map's other traits: rate_delay=0 below removes the debounce entirely, so
# every tick the browser reports publishes right away.
@render_lonboard(rate_delay=0)
def map():
    cities = gpd.read_file(CITIES_URL)
    return ScatterplotLayer.from_geopandas(cities, get_fill_color=[255, 60, 120], radius_min_pixels=4)


@render.code
def coords():
    vs = map.view_state()
    # map.read("view_state") is the same read -- "view_state" is a declared
    # accessor name, so read() just calls the accessor method
    agree = map.read("view_state") == vs
    return f"lon={vs.longitude:.4f} lat={vs.latitude:.4f} zoom={vs.zoom:.2f}\nmap.read('view_state') agrees: {agree}"
