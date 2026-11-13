# Title: World city explorer
# Summary: A clean starting point for a lonboard app: click a city for a
#     detail card, or drag a selection box for a filtered table. Swap in your
#     own GeoDataFrame and keep the accessor wiring.
# Bucket: template
# Widgets: lonboard, itables
# Pattern: click -> detail, box select -> table
# Run: uv run shiny run app.py
# Data: Natural Earth 110m populated places (public domain), fetched at startup
#   from a GitHub mirror
#
# Source: docs/widget-guides/lonboard/gallery/template_city_explorer.py

import geopandas as gpd
from lonboard import Map, ScatterplotLayer
from shapely.geometry import box
from shiny import req
from shiny.express import render, ui

from shinywidgets import render_itables, render_lonboard

ui.page_opts(title="World city explorer", fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"


def cities() -> gpd.GeoDataFrame:
    return gpd.read_file(CITIES_URL)


with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click a city, or drag the Select BBox tool")

        @render_lonboard
        def map():
            layer = ScatterplotLayer.from_geopandas(
                cities(),
                get_fill_color=[255, 60, 120],
                radius_min_pixels=4,
                pickable=True,
                auto_highlight=True,
            )
            # The cards below already show feature detail
            return Map(layer, show_side_panel=False)

    with ui.navset_card_tab():
        with ui.nav_panel("Detail"):

            @render.ui
            def detail():
                index = req(map.selected())
                row = cities().iloc[index]
                return ui.TagList(
                    ui.h5(row["NAME"]),
                    ui.p(row["ADM0NAME"]),
                    ui.p(f"Population: {int(row['POP_MAX']):,}"),
                )

        with ui.nav_panel("In selection"):

            @render_itables
            def table():
                bounds = req(map.selected_bounds())
                selected = cities()[cities().geometry.within(box(*bounds))]
                return selected[["NAME", "ADM0NAME", "POP_MAX"]].sort_values(
                    "POP_MAX", ascending=False
                )
