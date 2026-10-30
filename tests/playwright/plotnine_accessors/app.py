from __future__ import annotations

import pandas as pd
from plotnine import aes, geom_point, ggplot
from shiny import App, render, ui
from shinywidgets import output_widget, render_plotnine

app_ui = ui.page_fluid(
    output_widget("plot"),
    ui.output_text("clicked"),
)


def server(input, output, session):
    @render_plotnine
    def plot():
        df = pd.DataFrame({"x": range(10), "y": range(10)})
        return ggplot(df, aes("x", "y")) + geom_point()

    @render.text
    def clicked():
        e = plot.clicked()
        return "None" if e is None else f"{e.xdata:.2f},{e.ydata:.2f}"


app = App(app_ui, server)
