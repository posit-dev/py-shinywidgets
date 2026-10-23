from __future__ import annotations

from matplotlib.figure import Figure
from shiny import App, render, ui
from shinywidgets import output_widget, render_matplotlib

app_ui = ui.page_fluid(
    ui.input_action_button("bump", "Bump"),
    ui.output_text("count"),
    output_widget("bad"),
    output_widget("good"),
)


def server(input, output, session):
    @render.text
    def count():
        return str(input.bump())

    # Building the figure succeeds; drawing it fails (invalid mathtext)
    @render_matplotlib
    def bad():
        fig = Figure()
        fig.subplots().set_title(r"$\badcommand{x}$")
        return fig

    @render_matplotlib
    def good():
        fig = Figure()
        fig.subplots().plot([1, 2, 3])
        return fig


app = App(app_ui, server)
