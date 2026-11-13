import geopandas as gpd
from lonboard import Map, ScatterplotLayer
from lonboard.view_state import MapViewState
from shiny.express import render, ui
from shinywidgets import reactive_read, render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"

# map.selected() reports "whichever pickable layer was clicked most
# recently" -- it can't tell the two apart. With several pickable layers,
# read each layer's own `selected_index` trait instead.
CAPITALS = ["Paris", "Madrid", "Rome"]
OTHERS = ["Brussels", "Luxembourg", "Geneva", "Bern", "Andorra"]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_lonboard
        def map():
            cities = gpd.read_file(CITIES_URL).set_index("NAME")
            capitals = ScatterplotLayer.from_geopandas(
                cities.loc[CAPITALS].reset_index(),
                get_fill_color=[255, 60, 120],
                radius_min_pixels=10,
                pickable=True,
            )
            others = ScatterplotLayer.from_geopandas(
                cities.loc[OTHERS].reset_index(),
                get_fill_color=[80, 160, 255],
                radius_min_pixels=7,
                pickable=True,
            )
            return Map(
                [capitals, others],
                view_state=MapViewState(longitude=2.33, latitude=48.87, zoom=4.5),
                show_side_panel=False,
            )

    with ui.card():
        ui.card_header("Per-layer picks")

        @render.code
        def capital_pick():
            layer = map.widget.layers[0] if map.widget else None
            index = reactive_read(layer, "selected_index") if layer else None
            name = CAPITALS[index] if index is not None else None
            return f"capitals layer: {name}"

        @render.code
        def other_pick():
            layer = map.widget.layers[1] if map.widget else None
            index = reactive_read(layer, "selected_index") if layer else None
            name = OTHERS[index] if index is not None else None
            return f"others layer: {name}"
