import plotly.express as px
from keplergl import KeplerGl
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_keplergl

carshare = px.data.carshare().rename(
    columns={"centroid_lat": "lat", "centroid_lon": "lon"}
)
DEFAULT_CONFIG = {
    "version": "v1",
    "config": {"mapState": {"latitude": 45.53, "longitude": -73.6, "zoom": 10}},
}

saved_config = reactive.value(None)

ui.page_opts(title="Saving and restoring a view", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_keplergl
        def map():
            return KeplerGl(data={"data": carshare}, config=DEFAULT_CONFIG)

    with ui.card():
        ui.input_action_button("save", "Save current view")
        ui.input_action_button("reset", "Reset to default")
        ui.input_action_button("restore", "Restore saved view")

        @render.code
        def saved_view():
            cfg = saved_config.get()
            if cfg is None:
                return "No view saved yet."
            state = cfg.get("config", {}).get("mapState", {})
            return (
                f"saved zoom: {state.get('zoom', 0):.2f}, "
                f"lat: {state.get('latitude', 0):.3f}"
            )


# The whole config -- not just mapState -- round-trips, so this also
# preserves any layers, colors, or filters the user set up in kepler's UI.
@reactive.effect
@reactive.event(input.save)
def _():
    saved_config.set(map.read("config"))


@reactive.effect
@reactive.event(input.reset)
def _():
    map.widget.config = DEFAULT_CONFIG


@reactive.effect
@reactive.event(input.restore)
def _():
    if saved_config.get() is not None:
        map.widget.config = saved_config.get()
