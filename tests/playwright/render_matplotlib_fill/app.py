from __future__ import annotations

import matplotlib.pyplot as plt
from shiny import App, ui
from shinywidgets import output_widget, render_matplotlib

app_ui = ui.page_fillable(
    ui.card(
        ui.card_header("matplotlib in a fillable card"),
        output_widget("mpl"),
        full_screen=True,
    )
)


def server(input, output, session):
    @render_matplotlib
    def mpl():
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3, 4], [1, 4, 2, 3])
        ax.set_title("fill test")
        return fig


app = App(app_ui, server)
