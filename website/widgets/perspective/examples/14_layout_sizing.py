from __future__ import annotations

import plotly.express as px
from shiny.express import ui
from shinywidgets import render_perspective

ui.page_opts(title="Layout and sizing", fillable=True)

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])

with ui.card(full_screen=True, height="400px"):

    @render_perspective
    def grid():
        return countries
