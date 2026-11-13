# Box-select stations on the map to filter a table below it. BoundsXY reports
# the dragged rectangle in lon/lat, so the same bounds test a plain pandas
# DataFrame -- no re-projection needed on the Shiny side.
import geoviews as gv
import holoviews as hv
import plotly.express as px
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

carshare = px.data.carshare()
bounds_val = reactive.value(None)

ui.page_opts(title="Box-select stations to filter a table", fillable=True)

with ui.card(full_screen=True):

    @render_holoviews
    def map():
        points = gv.Points(
            carshare, kdims=["centroid_lon", "centroid_lat"], vdims=["car_hours"]
        ).opts(
            color="car_hours",
            cmap="viridis",
            size=8,
            tools=["box_select"],
            active_tools=["box_select"],
        )
        hv.streams.BoundsXY(source=points).add_subscriber(
            lambda bounds: bounds_val.set(bounds)
        )
        return (gv.tile_sources.OSM * points).opts(responsive=True)


with ui.card():
    ui.card_header("Stations in view")

    @render.data_frame
    def selected():
        b = bounds_val()
        if b is None:
            return carshare.iloc[:0]
        x0, y0, x1, y1 = b
        sel = carshare[
            carshare.centroid_lon.between(x0, x1) & carshare.centroid_lat.between(y0, y1)
        ]
        return render.DataGrid(sel.round(2), height="220px")
