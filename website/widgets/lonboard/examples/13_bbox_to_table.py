import geopandas as gpd
from lonboard import Map, ScatterplotLayer
from shapely.geometry import box
from shiny import req
from shiny.express import ui
from shinywidgets import render_itables, render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click the Select BBox button, then click two corners")

        @render_lonboard
        def map():
            cities = gpd.read_file(CITIES_URL)
            layer = ScatterplotLayer.from_geopandas(
                cities, get_fill_color=[255, 60, 120], radius_min_pixels=4
            )
            return Map(layer, show_side_panel=False)

    with ui.card():
        ui.card_header("Cities in the selected box")

        @render_itables
        def table():
            bounds = req(map.selected_bounds())
            cities = gpd.read_file(CITIES_URL)
            selected = cities[cities.geometry.within(box(*bounds))]
            return selected[["NAME", "ADM0NAME", "POP_MAX"]].sort_values(
                "POP_MAX", ascending=False
            )
