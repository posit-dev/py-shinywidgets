from __future__ import annotations

import plotly.express as px
from perspective import Server
from perspective.widget import PerspectiveWidget
from shiny.express import ui
from shinywidgets import render_perspective

ui.page_opts(title="Pivoting", fillable=True)

# Two snapshots 55 years apart, so a continent x year pivot tells a story
countries = px.data.gapminder().query("year in [1952, 2007]")


@render_perspective
def grid():
    # A bare DataFrame return gets a private per-session table for you, but
    # there's nowhere to pass pivot config -- build the table yourself so it
    # can go to the PerspectiveWidget constructor.
    table = Server().new_local_client().table(countries)
    return PerspectiveWidget(
        table,
        columns=["pop"],
        group_by=["continent"],
        split_by=["year"],
        aggregates={"pop": "sum"},
    )
