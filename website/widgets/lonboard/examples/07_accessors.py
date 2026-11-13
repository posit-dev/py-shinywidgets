import geopandas as gpd
from lonboard import Map, ScatterplotLayer
from lonboard.view_state import MapViewState
from shiny.express import render, ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"
FOCUS = ["Paris", "London", "Berlin", "Madrid", "Rome"]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_lonboard
        def map():
            cities = gpd.read_file(CITIES_URL)
            cities = cities[cities.NAME.isin(FOCUS)].reset_index(drop=True)
            layer = ScatterplotLayer.from_geopandas(
                cities, get_fill_color=[255, 60, 120], radius_min_pixels=12, pickable=True
            )
            return Map(
                layer,
                view_state=MapViewState(longitude=2.33, latitude=48.87, zoom=4.2),
                # Keep the canvas size stable; the "Accessors" card already
                # shows feature detail via selected()
                show_side_panel=False,
            )

    with ui.card():
        ui.card_header("Accessors")

        @render.code
        def view_state():
            vs = map.view_state()
            return f"view_state()\n  lon={vs.longitude:.2f} lat={vs.latitude:.2f} zoom={vs.zoom:.2f}"

        @render.code
        def selected():
            return f"selected()\n  {map.selected()}"

        @render.code
        def selected_bounds():
            return f"selected_bounds()\n  {map.selected_bounds()}"

        @render.code
        def clicked():
            return f"clicked()\n  {map.clicked()}"
