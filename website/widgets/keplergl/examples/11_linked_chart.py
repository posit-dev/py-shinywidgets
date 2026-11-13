import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_keplergl, render_plotly

carshare = px.data.carshare().rename(
    columns={"centroid_lat": "lat", "centroid_lon": "lon"}
)

ui.page_opts(title="One input, two linked views", fillable=True)
ui.input_slider("min_hours", "Minimum car-share hours", 0, 3000, 0, step=100)


def filtered():
    return carshare[carshare["car_hours"] >= input.min_hours()]


with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_keplergl
        def map():
            with reactive.isolate():
                return filtered()

    with ui.card(full_screen=True):

        @render_plotly
        def hist():
            fig = px.histogram(filtered(), x="car_hours", nbins=20)
            fig.update_layout(
                title=f"{len(filtered())} stations", margin=dict(t=40)
            )
            return fig


@reactive.effect
@reactive.event(input.min_hours)
def _():
    # Both views come from the same `filtered()` call: the map updates in
    # place (preserving its camera and any styling), and the histogram
    # re-renders -- cheap, since it's an ordinary plotly figure.
    map.widget.data = {"data": filtered()}
