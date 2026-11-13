from __future__ import annotations

import plotly.express as px
from shiny.express import ui
from shinywidgets import render_perspective

ui.page_opts(title="Perspective quickstart", fillable=True)

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])


@render_perspective
def grid():
    return countries
