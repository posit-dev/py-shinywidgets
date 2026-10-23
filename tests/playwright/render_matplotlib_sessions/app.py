from __future__ import annotations

import matplotlib.pyplot as plt
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_matplotlib

app_ui = ui.page_fluid(
    ui.input_action_button("redraw", "Redraw"),
    ui.output_text("lines"),
    output_widget("mpl"),
)


def server(input, output, session):
    @render_matplotlib
    def mpl():
        input.redraw()
        # The seaborn idiom (e.g., sns.histplot() without ax=): draw on pyplot's
        # current axes, which are shared by every session in the process
        ax = plt.gca()
        ax.plot([1, 2, 3], label=session.id)
        return ax

    @render.text
    def lines():
        canvas = mpl.widget
        if canvas is None:
            return ""
        with reactive.isolate():
            return " ".join(
                line.get_label() for ax in canvas.figure.axes for line in ax.lines
            )


app = App(app_ui, server)
