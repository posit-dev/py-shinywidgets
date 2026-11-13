import plotly.express as px
from shiny.express import ui

import globals  # noqa: F401 -- locks down DuckDB once per process; see globals.py
from shinywidgets import render_pygwalker

ui.page_opts(fillable=True)

tips = px.data.tips()


@render_pygwalker
def explorer():
    return tips
