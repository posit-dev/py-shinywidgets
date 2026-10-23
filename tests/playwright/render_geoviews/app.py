from __future__ import annotations

import geoviews as gv
import holoviews as hv
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_holoviews

hv.extension("bokeh")

CITIES = [(-122.4, 37.8), (-0.1, 51.5), (139.7, 35.7)]

app_ui = ui.page_fillable(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.layout_columns(
        ui.card(output_widget("tiles"), id="tiles_card", style="height: 400px;"),
        ui.card(output_widget("fixed"), id="fixed_card", style="height: 400px;"),
        ui.card(output_widget("dynamic"), id="dynamic_card", style="height: 400px;"),
        ui.card(output_widget("polygons"), id="polygons_card", style="height: 400px;"),
        col_widths=6,
        row_heights="400px",
    ),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    # Web map tiles under points
    @render_holoviews
    def tiles():
        counter.get()
        points = gv.Points(CITIES).opts(color="red", size=12)
        return (gv.tile_sources.OSM * points).opts(responsive=True)

    # An explicit size, which must be respected
    @render_holoviews
    def fixed():
        return gv.Points(CITIES).opts(color="red", size=12, width=350, height=250)

    # Panel's HoloViews pane wires the DynamicMap's kdim to a widget; changing it
    # makes the browser call back into Python, which returns new points
    @render_holoviews
    def dynamic():
        return (
            gv.DynamicMap(lambda lon: gv.Points([(lon, 0)]), kdims="lon")
            .redim.range(lon=(-120, 120))
            .opts(
                color="red",
                size=20,
                xlim=(-180, 180),
                ylim=(-90, 90),
                responsive=True,
            )
        )

    # No tiles, so this one draws without any network access
    @render_holoviews
    def polygons():
        return gv.Polygons([[(-100, -40), (100, -40), (100, 40), (-100, 40)]]).opts(
            color="red", responsive=True
        )


app = App(app_ui, server)
