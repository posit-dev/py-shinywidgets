from __future__ import annotations

import plotly.express as px
from perspective import Server
from perspective.widget import PerspectiveWidget
from shiny.express import ui
from shinywidgets import render_perspective

ui.page_opts(title="Plugins", fillable=True)

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])


@render_perspective
def grid():
    # Same data, same aggregation -- just a different plugin. Perspective
    # also ships X/Y Bar, X/Y Line, X/Y Scatter, Sunburst, Heatmap,
    # Candlestick, and OHLC; switch `plugin` to try any of them.
    table = Server().new_local_client().table(countries)
    return PerspectiveWidget(
        table,
        plugin="Treemap",
        # Without "columns", the Treemap sizes rectangles by the first
        # numeric column -- the auto-added pandas "index" -- instead of pop
        columns=["pop"],
        group_by=["continent", "country"],
        aggregates={"pop": "sum"},
    )
