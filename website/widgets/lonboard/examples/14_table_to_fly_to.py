import geopandas as gpd
from itables.widget import ITable
from lonboard import ScatterplotLayer
from shiny import reactive, req
from shiny.express import ui
from shinywidgets import render_itables, render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"


@reactive.calc
def cities() -> gpd.GeoDataFrame:
    return gpd.read_file(CITIES_URL).nlargest(20, "POP_MAX").reset_index(drop=True)


with ui.layout_columns(col_widths=[5, 7]):
    with ui.card():
        ui.card_header("Pick a city")

        @render_itables
        def table():
            df = cities()[["NAME", "ADM0NAME", "POP_MAX"]]
            return ITable(df, select=True, lengthMenu=[20])

    with ui.card(full_screen=True):

        @render_lonboard
        def map():
            return ScatterplotLayer.from_geopandas(
                cities(), get_fill_color=[255, 60, 120], radius_min_pixels=5
            )


@reactive.effect
def _fly_to_selected():
    rows = req(table.selected_rows())
    row = cities().iloc[rows[0]]
    # table drives the map: selecting a row flies the camera there, without
    # re-sending the 20 points or losing any in-place styling
    map.widget.fly_to(longitude=row.LONGITUDE, latitude=row.LATITUDE, zoom=8, duration=1200)
