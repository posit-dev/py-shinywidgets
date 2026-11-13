from __future__ import annotations

import plotly.express as px
from perspective import Server
from perspective.widget import PerspectiveWidget
from shiny.express import ui
from shinywidgets import render_perspective

ui.page_opts(title="Expressions", fillable=True)

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])


@render_perspective
def grid():
    # Expressions add a computed column, written in Perspective's own
    # expression language (column names are double-quoted). It's evaluated
    # in the table's engine, so it stays live across pivots and updates.
    table = Server().new_local_client().table(countries)
    return PerspectiveWidget(
        table,
        columns=["country", "pop", "gdpPercap", "gdp_billions"],
        expressions={"gdp_billions": '("gdpPercap" * "pop") / 1000000000'},
    )
