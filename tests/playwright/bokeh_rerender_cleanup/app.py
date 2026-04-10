from __future__ import annotations

from bokeh.plotting import figure
from shiny import App, reactive, ui
from shinywidgets import bokeh_dependency, output_widget, render_bokeh


app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    output_widget("plot"),
    bokeh_dependency(),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render_bokeh
    def plot():
        n = counter.get()
        p = figure(title=f"render {n}")
        p.line([1, 2, 3], [n, n + 1, n + 2], line_width=2)
        return p


app = App(app_ui, server)
