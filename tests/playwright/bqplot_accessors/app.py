from __future__ import annotations

import bqplot
from bqplot.interacts import BrushIntervalSelector, BrushSelector
from shiny import App, render, ui
from shinywidgets import output_widget, render_bqplot

x = [float(i) for i in range(11)]
y = [float((i * 3) % 11) for i in range(11)]

app_ui = ui.page_fluid(
    output_widget("fig1", height="300px"),
    ui.output_text("sel1"),
    output_widget("fig2", height="300px"),
    ui.output_text("brush2"),
)


def scatter_figure(two_d: bool) -> bqplot.Figure:
    x_sc, y_sc = bqplot.LinearScale(min=0, max=10), bqplot.LinearScale()
    mark = bqplot.Scatter(x=x, y=y, scales={"x": x_sc, "y": y_sc})
    # A selector only updates the marks (and reports in the scales) it's given
    if two_d:
        interaction = BrushSelector(x_scale=x_sc, y_scale=y_sc, marks=[mark])
    else:
        interaction = BrushIntervalSelector(scale=x_sc, marks=[mark])
    return bqplot.Figure(
        marks=[mark],
        axes=[
            bqplot.Axis(scale=x_sc),
            bqplot.Axis(scale=y_sc, orientation="vertical"),
        ],
        interaction=interaction,
    )


def server(input, output, session):
    @render_bqplot
    def fig1():
        return scatter_figure(two_d=True)

    @render.text
    def sel1():
        return str(
            [None if s is None else sorted(int(i) for i in s) for s in fig1.selection()]
        )

    @render_bqplot
    def fig2():
        return scatter_figure(two_d=False)

    @render.text
    def brush2():
        b = fig2.brush()
        return str(None if b is None else b.tolist())


app = App(app_ui, server)
