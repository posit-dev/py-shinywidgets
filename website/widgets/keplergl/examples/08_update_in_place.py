import plotly.express as px
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_keplergl

carshare = px.data.carshare().rename(
    columns={"centroid_lat": "lat", "centroid_lon": "lon"}
)

ui.page_opts(title="Updating data in place", fillable=True)
ui.input_slider("min_hours", "Minimum car-share hours", 0, 3000, 0, step=100)


def filtered():
    return carshare[carshare["car_hours"] >= input.min_hours()]


@render_keplergl
def map():
    # Read the input under isolate(): this render function only runs once
    # (on first display). The effect below keeps the data current.
    with reactive.isolate():
        return filtered()


@reactive.effect
@reactive.event(input.min_hours)
def _():
    # Swapping `.widget.data` in place sends only the new rows (kilobytes),
    # keeps the map mounted, and preserves any layer/filter/camera changes
    # the user made in kepler's side panel. Re-returning a new value from
    # `map()` instead would re-send kepler's ~13 MB bundle and reset the UI.
    map.widget.data = {"data": filtered()}
