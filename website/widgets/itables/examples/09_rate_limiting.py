from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import reactive_read, render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="Rate limiting", fillable=True)

# selected_rows() fires once per click, not a continuous stream, so there's
# nothing to smooth there: rate_policy/rate_delay has no effect on it. They
# rate-limit reactive_read() on the widget instead -- useful if several rapid
# clicks (e.g. shift-click across many rows) would otherwise each trigger an
# expensive recompute.
with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_itables(rate_policy="debounce", rate_delay=1)
        def table():
            return ITable(countries, select=True)

    with ui.card():
        ui.card_header("Fires per click")
        accessor_count = reactive.value(0)
        read_count = reactive.value(0)

        @reactive.effect
        def _count_accessor():
            table.selected_rows()
            with reactive.isolate():
                accessor_count.set(accessor_count() + 1)

        @reactive.effect
        def _count_reactive_read():
            req(table.widget)
            reactive_read(table.widget, "selected_rows")
            with reactive.isolate():
                read_count.set(read_count() + 1)

        @render.code
        def counts():
            return (
                f"table.selected_rows(): {accessor_count()}\n"
                f"reactive_read() debounced 1s: {read_count()}"
            )
