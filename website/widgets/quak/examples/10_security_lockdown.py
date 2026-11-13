from __future__ import annotations

import plotly.express as px
from shiny.express import ui
from shinywidgets import render_quak

ui.page_opts(title="quak with an unrestricted connection (local use only)", fillable=True)

gapminder = px.data.gapminder()

with ui.card(full_screen=True):

    @render_quak(allow_unrestricted_connection=True)
    def table():
        # render_quak() locks down the table's DuckDB connection by default
        # (see Gotchas): a visitor's browser can query the data but can't
        # read server files or change the connection's settings. Opting out
        # here leaves the connection exactly as quak builds it -- only do
        # this for a local, single-user app, never one you deploy.
        return gapminder
