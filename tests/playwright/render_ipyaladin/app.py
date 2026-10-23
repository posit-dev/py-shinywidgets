from __future__ import annotations

from ipyaladin import Aladin
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipyaladin

app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(output_widget("sky")),
        ui.card(output_widget("sky_fixed")),
        ui.card(output_widget("sky_output_height", height="300px")),
        # An output with no definite height to fill (and no explicit height)
        ui.div(output_widget("sky_unfillable", fillable=False)),
    ),
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("target"),
    ui.output_text("fov"),
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

    # The Crab nebula (synthetic coordinates; no name resolution needed)
    @render_ipyaladin
    def sky():
        input.rerender()
        return Aladin(target=(83.63, 22.01), fov=10)

    @render_ipyaladin
    def sky_fixed():
        return Aladin(target=(83.63, 22.01), fov=10, height=250)

    @render_ipyaladin
    def sky_output_height():
        return Aladin(target=(83.63, 22.01), fov=10)

    @render_ipyaladin
    def sky_unfillable():
        return Aladin(target=(83.63, 22.01), fov=10)

    @render.text
    def target():
        return str(reactive_read(sky.widget, "_target"))

    @render.text
    def fov():
        return f"{reactive_read(sky.widget, '_fov'):.4f}"


app = App(app_ui, server)
