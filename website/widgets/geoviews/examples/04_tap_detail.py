# Click a station on the map to see its details. hv.streams.Tap reports the
# click in data coordinates (lon/lat), even though the map draws in Web
# Mercator -- geoviews un-projects it for you. Same recipe as the holoviews
# guide's Tap example; see ../holoviews/guide.md#the-recipe.
import geoviews as gv
import holoviews as hv
import plotly.express as px
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

carshare = px.data.carshare()
tap_xy = reactive.value(None)

ui.page_opts(title="Click a station for details", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_holoviews
        def map():
            points = gv.Points(
                carshare, kdims=["centroid_lon", "centroid_lat"], vdims=["car_hours"]
            ).opts(color="car_hours", cmap="viridis", size=8, tools=["tap", "hover"])
            hv.streams.Tap(source=points).add_subscriber(
                lambda x, y: tap_xy.set((x, y))
            )
            return (gv.tile_sources.OSM * points).opts(responsive=True)

    with ui.card():
        ui.card_header("Nearest station")

        @render.ui
        def detail():
            xy = tap_xy()
            if xy is None:
                return ui.p("Click a station on the map.", class_="text-muted")
            x, y = xy
            dist = (carshare.centroid_lon - x) ** 2 + (carshare.centroid_lat - y) ** 2
            row = carshare.loc[dist.idxmin()]
            return ui.TagList(
                ui.h5(f"{row.car_hours:.0f} car-hours"),
                ui.p(f"Peak hour: {row.peak_hour:.0f}:00"),
                ui.p(f"{row.centroid_lat:.4f}, {row.centroid_lon:.4f}", class_="text-muted"),
            )
