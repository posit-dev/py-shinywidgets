from __future__ import annotations

import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_perspective

ui.page_opts(title="filter() accessor", fillable=True)

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])


@render_perspective
def grid():
    return countries


@render.code
def filter_state():
    # filter() seeds at [] and never goes None, so "no filter set" and
    # "nothing reported yet" are the same value -- no req()/not-ready
    # handling needed.
    return str(grid.filter())
