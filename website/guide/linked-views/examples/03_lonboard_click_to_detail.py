import geopandas as gpd
from lonboard import Map, ScatterplotLayer
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"


with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_lonboard
        def map():
            cities = gpd.read_file(CITIES_URL)
            layer = ScatterplotLayer.from_geopandas(
                cities,
                get_fill_color=[255, 60, 120],
                radius_min_pixels=4,
                pickable=True,
                auto_highlight=True,
            )
            # The "Selected city" card already shows feature detail
            return Map(layer, show_side_panel=False)

    with ui.card():
        ui.card_header("Selected city")

        @render.ui
        def detail():
            # selected_rows() is the picked row itself, taken from the
            # layer's own data -- no second read of the file, no iloc. It's
            # an empty frame until the first pick; req() waits instead of
            # showing an empty card on load.
            rows = map.selected_rows()
            req(len(rows) > 0)
            row = rows.iloc[0]
            return ui.TagList(
                ui.h5(row["NAME"]),
                ui.p(row["ADM0NAME"]),
                ui.p(f"Population: {int(row['POP_MAX']):,}"),
            )
