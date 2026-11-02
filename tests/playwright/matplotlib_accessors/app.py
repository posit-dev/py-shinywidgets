from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_matplotlib

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    output_widget("plot"),
    ui.output_text("clicked"),
    ui.output_text("picked"),
    ui.output_text("limits"),
    ui.output_text("click_count"),
)


def server(input, output, session):
    n_evals = [0]

    @render_matplotlib
    def plot():
        input.rerender()
        fig = Figure(figsize=(4, 3))
        ax = fig.subplots()
        # A horizontal line of many points, so a center-canvas click is on it
        ax.plot(np.linspace(0, 1, 21), [0.5] * 21, picker=20)
        # Keep the toolbar shown (the default 'auto' hides it until hover)
        from shinywidgets import as_widget

        canvas = as_widget(fig)
        canvas.toolbar_visible = "visible"
        return canvas

    @reactive.calc
    def last_click():
        n_evals[0] += 1
        return plot.clicked()

    @render.text
    def clicked():
        e = last_click()
        return "None" if e is None else f"{e.xdata:.2f},{e.ydata:.2f}"

    @render.text
    def picked():
        e = plot.picked()
        return "None" if e is None else ",".join(str(i) for i in e.ind)

    @render.text
    def limits():
        (x0, x1), (y0, y1) = plot.limits()
        return f"{x0:.2f},{x1:.2f},{y0:.2f},{y1:.2f}"

    @render.text
    def click_count():
        last_click()
        return str(n_evals[0])


app = App(app_ui, server)
