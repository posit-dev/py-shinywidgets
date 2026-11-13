# A world population choropleth from a real GeoDataFrame, two ways: explicit
# gv.Polygons, and hvPlot's one-line `geo=True` shortcut. Downloads Natural
# Earth's 110m country polygons (~200KB) on first run.
import geopandas as gpd
import geoviews as gv
import holoviews as hv
import hvplot.pandas  # noqa: F401
from shiny.express import ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

NE_COUNTRIES = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
world = gpd.read_file(NE_COUNTRIES)
world = world[world.POP_EST > 0]  # a few disputed territories have no estimate

ui.page_opts(title="World population (Natural Earth, 110m)", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("gv.Polygons, explicit")

        @render_holoviews
        def explicit():
            return gv.Polygons(
                world, vdims=["NAME", "POP_EST"]
            ).opts(
                color="POP_EST",
                cmap="viridis",
                logz=True,
                colorbar=True,
                tools=["hover"],
                responsive=True,
            )

    with ui.card(full_screen=True):
        ui.card_header("hvPlot, geo=True")

        @render_holoviews
        def shortcut():
            return world.hvplot(
                c="POP_EST",
                geo=True,
                cmap="viridis",
                logz=True,
                hover_cols=["NAME"],
                responsive=True,
            )
