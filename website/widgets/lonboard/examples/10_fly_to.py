import geopandas as gpd
from lonboard import ScatterplotLayer
from lonboard.view_state import MapViewState
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"
DESTINATIONS = {
    "Tokyo": (139.75, 35.68, 9),
    "Nairobi": (36.82, -1.29, 9),
    "Buenos Aires": (-58.38, -34.6, 9),
    "World": (10, 20, 1),
}

ui.input_select("city", "Fly to", list(DESTINATIONS))

with ui.card(full_screen=True):

    @render_lonboard
    def map():
        cities = gpd.read_file(CITIES_URL)
        layer = ScatterplotLayer.from_geopandas(
            cities, get_fill_color=[255, 60, 120], radius_min_pixels=4
        )
        return layer  # starts at the default world view


@reactive.effect
@reactive.event(input.city)
def _fly_to_city():
    lon, lat, zoom = DESTINATIONS[input.city()]
    # fly_to() animates the camera in the browser; it doesn't touch the
    # data, so nothing is re-sent and any selection/styling is preserved
    map.widget.fly_to(longitude=lon, latitude=lat, zoom=zoom, duration=1200)
