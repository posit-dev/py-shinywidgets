from __future__ import annotations

import bqplot
import plotly.express as px
from shiny import reactive, req
from shiny.express import input, render, ui
from shinywidgets import reactive_read, render_bqplot, render_plotly

df = px.data.gapminder().query("year == 2007")

ui.page_opts(title="Fill vs. fixed height", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Fills the card (no explicit height)")

        @render_plotly
        def fills():
            return px.scatter(df, x="gdpPercap", y="lifeExp", log_x=True)

    with ui.card():
        ui.card_header('render_plotly(height="220px")')

        @render_plotly(height="220px")
        def fixed():
            return px.scatter(df, x="gdpPercap", y="lifeExp", log_x=True)


ui.card_header(
    "Click the button: widget.layout.height changes, but nothing moves "
    "(bqplot, no explicit height, still filling)"
)
with ui.card():
    ui.input_action_button("resize", "Set widget.layout.height = '150px'")

    @render_bqplot
    def line():
        x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
        mark = bqplot.Lines(x=[1, 2, 3, 4], y=[1, 3, 2, 4], scales={"x": x_sc, "y": y_sc})
        return bqplot.Figure(
            marks=[mark],
            axes=[bqplot.Axis(scale=x_sc), bqplot.Axis(scale=y_sc, orientation="vertical")],
        )

    @render.text
    def height_trait():
        widget = line.widget
        req(widget)
        return f"widget.layout.height = {reactive_read(widget.layout, 'height')!r}"

    @reactive.effect
    @reactive.event(input.resize)
    def _set_height():
        with reactive.isolate():
            widget = line.widget
        if widget is not None:
            # A plain ipywidgets.Layout(height=...) set after the figure is
            # already on screen and filling: the trait changes (height_trait()
            # above re-renders to show it), but the figure's size doesn't,
            # because filling is CSS (flex: 1 1 auto) applied once at render
            # time -- set_layout_defaults() only reads layout.height to decide
            # the *initial* fill flag, not on every later change.
            widget.layout.height = "150px"
