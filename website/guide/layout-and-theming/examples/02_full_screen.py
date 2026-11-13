from __future__ import annotations

import plotly.express as px
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007")

ui.page_opts(title="full_screen=True", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Hover and click the expand icon (top right)")

        @render_plotly
        def scatter():
            return px.scatter(
                df, x="gdpPercap", y="lifeExp", color="continent", log_x=True
            )

    with ui.card():
        ui.card_header("A plain card, for contrast")
        "This card has no full_screen=True, so it has no expand icon."
