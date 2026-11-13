# A quick-start geoviews map: a tile basemap plus a scatter of real points,
# sized and colored by two more columns. Pan, zoom, and hover all come free.
import geoviews as gv
import holoviews as hv
import plotly.express as px
from shiny.express import ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

carshare = px.data.carshare()

ui.page_opts(title="Montreal car-share stations", fillable=True)


@render_holoviews
def map():
    points = gv.Points(
        carshare, kdims=["centroid_lon", "centroid_lat"], vdims=["car_hours", "peak_hour"]
    ).opts(
        color="car_hours",
        cmap="viridis",
        size=8,
        colorbar=True,
        tools=["hover"],
        title="Car-share hours by station",
    )
    return (gv.tile_sources.OSM * points).opts(responsive=True)
