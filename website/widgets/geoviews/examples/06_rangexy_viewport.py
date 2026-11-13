# The visible viewport drives two value boxes. hv.streams.RangeXY reports the
# current x_range/y_range in the *source element's* coordinates -- lon/lat for
# a geoviews element, same as BoundsXY/Tap -- even though the plot itself
# draws in Web Mercator underneath the tiles.
#
# Store the stream's own (idempotent) range tuple, never a counter: a stream
# that fires on every animation frame of a zoom, combined with an
# ever-different subscriber value, causes a render loop (see Gotchas).
import geoviews as gv
import holoviews as hv
import plotly.express as px
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

carshare = px.data.carshare()
range_val = reactive.value(None)

ui.page_opts(title="Viewport drives value boxes", fillable=True)

with ui.layout_columns(fill=False):
    with ui.value_box():
        "Stations visible"

        @render.text
        def n_visible():
            return str(len(visible()))

    with ui.value_box():
        "Avg car-hours (visible)"

        @render.text
        def avg_hours():
            v = visible()
            return f"{v.car_hours.mean():.0f}" if len(v) else "-"


with ui.card(full_screen=True):

    @render_holoviews
    def map():
        points = gv.Points(
            carshare, kdims=["centroid_lon", "centroid_lat"], vdims=["car_hours"]
        ).opts(
            color="car_hours", cmap="viridis", size=8,
            tools=["wheel_zoom"], active_tools=["wheel_zoom"],
        )
        hv.streams.RangeXY(source=points).add_subscriber(
            lambda x_range, y_range: range_val.set((x_range, y_range))
        )
        return (gv.tile_sources.OSM * points).opts(responsive=True)


@reactive.calc
def visible():
    r = range_val()
    if r is None or None in r[0] or None in r[1]:
        return carshare
    (lon0, lon1), (lat0, lat1) = r
    return carshare[
        carshare.centroid_lon.between(lon0, lon1)
        & carshare.centroid_lat.between(lat0, lat1)
    ]
