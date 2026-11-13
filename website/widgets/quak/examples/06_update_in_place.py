from __future__ import annotations

import plotly.express as px
import quak
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_quak

ui.page_opts(title="quak: resize in place vs. re-render")

gapminder = px.data.gapminder()

ui.input_action_button("grow", "Grow the table (in place)")
ui.input_action_button("rerender", "Re-render the table")


@render.code
def sql():
    return table.sql()


with ui.card():
    # A roomy fixed height on the output itself, so toggling the widget's own
    # (smaller) layout.height below is never clipped by the output container.
    @render_quak(height="700px")
    def table():
        # Brush or sort, then click "Re-render": this function re-runs and
        # builds a brand-new quak.Widget, so the filter/sort is gone -- quak
        # has no way to hand a filter back in on construction.
        input.rerender()
        widget = quak.Widget(gapminder)
        widget.layout.height = "250px"
        return widget


@reactive.effect
@reactive.event(input.grow)
def _():
    # Mutating the already-rendered widget keeps the same quak instance, and
    # so keeps whatever the user had brushed or sorted, unlike re-rendering.
    current = table.widget.layout.height
    table.widget.layout.height = "650px" if current != "650px" else "250px"
