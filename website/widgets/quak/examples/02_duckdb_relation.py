from __future__ import annotations

import duckdb
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_quak

ui.page_opts(title="quak from a DuckDB relation", fillable=True)

# Register once; render_quak() also accepts pandas/polars DataFrames and
# pyarrow Tables directly, with no conversion step. DuckDBPyConnection.register()
# returns the connection (for chaining) -- discard it, or Shiny Express's
# auto-display will try to render that return value as page content.
con = duckdb.connect(":memory:")
_ = con.register("gapminder", px.data.gapminder())
by_country_year = con.sql("""
    select country, continent, year, lifeExp, pop, gdpPercap
    from gapminder
    where pop > 2_000_000
""")

with ui.card(full_screen=True):

    @render_quak
    def table():
        return by_country_year
