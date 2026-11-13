from __future__ import annotations

import plotly.express as px
from shiny.express import ui
from shinywidgets import render_quak

ui.page_opts(title="quak quickstart", fillable=True)

gapminder = px.data.gapminder()

with ui.card(full_screen=True):

    @render_quak
    def table():
        return gapminder
