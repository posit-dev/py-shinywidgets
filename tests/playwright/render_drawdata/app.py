from __future__ import annotations

from drawdata import BarWidget, ScatterWidget
from shiny import App, ui
from shinywidgets import output_widget, render_drawdata

# Explicit-height outputs: with the width caps lifted (js/src/fill.ts), the
# charts would scale to the 1200px width and outgrow (and get clipped by)
# these heights unless the fit also constrains by height. The filling output
# checks the same fit in a fill layout.
app_ui = ui.page_fillable(
    ui.card(
        ui.card_header("ScatterWidget (intrinsic 800x400)"),
        output_widget("scatter", width="1200px", height="500px"),
        fill=False,
    ),
    ui.card(
        ui.card_header("BarWidget (intrinsic 800x550)"),
        output_widget("bars", width="1200px", height="400px"),
        fill=False,
    ),
    ui.card(
        ui.card_header("ScatterWidget (filling)"),
        output_widget("fill_scatter"),
    ),
)


def server(input, output, session):
    @render_drawdata
    def scatter():
        return ScatterWidget()

    @render_drawdata
    def bars():
        return BarWidget()

    @render_drawdata
    def fill_scatter():
        return ScatterWidget()


app = App(app_ui, server)
