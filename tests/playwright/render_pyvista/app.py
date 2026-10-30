from __future__ import annotations

import pyvista as pv
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_pyvista

pv.OFF_SCREEN = True

app_ui = ui.page_fillable(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.card(
        ui.card_header("pyvista in a fillable card"),
        output_widget("plot"),
        full_screen=True,
    ),
    output_widget("plot_fixed", height="300px"),
)


def make_plotter() -> "pv.Plotter":
    pl = pv.Plotter(window_size=[400, 300])
    pl.add_mesh(pv.Sphere(), color="orange", show_edges=True)
    return pl


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_pyvista
    def plot():
        input.rerender()
        return make_plotter()

    @render_pyvista
    def plot_fixed():
        return make_plotter()


app = App(app_ui, server)
