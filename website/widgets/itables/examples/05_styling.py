from __future__ import annotations

import plotly.express as px
from itables import JavascriptFunction
from itables.widget import ITable
from shiny.express import ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="Cell formatting and styling", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("A formatted column and conditional cell colors")

    @render_itables
    def table():
        return ITable(
            countries,
            columnDefs=[
                {
                    # Format gdpPercap (column index 4) as currency on display,
                    # but keep the raw number for sorting/filtering.
                    "targets": [4],
                    "render": JavascriptFunction(
                        "function(data, type) {"
                        "  return type === 'display' "
                        "    ? '$' + Number(data).toLocaleString() : data;"
                        "}"
                    ),
                },
                {
                    # Color the life-expectancy cell by value. Without a
                    # `render` of its own, this column's cell data arrives as
                    # itables' own [display_string, raw_number] pair, not a
                    # plain number -- index into it rather than comparing it
                    # directly.
                    "targets": [2],
                    "createdCell": JavascriptFunction(
                        "function(td, data) {"
                        "  var v = Array.isArray(data) ? data[1] : data;"
                        "  td.style.color = v < 60 ? '#c0392b'"
                        "    : v >= 75 ? '#1e8449' : '';"
                        "}"
                    ),
                },
            ],
        )
