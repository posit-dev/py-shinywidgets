from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny import reactive, req
from shiny.express import input, render, ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)
continents = ["All", *sorted(countries["continent"].unique())]

TABLE_OPTS = {"select": True, "buttons": ["copyHtml5"]}

ui.page_opts(title="Filter keeps the selection", fillable=True)

ui.input_select("continent", "Continent", continents)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_itables
        def table():
            return ITable(countries, **TABLE_OPTS)

    with ui.card():
        ui.card_header("Still selected after filtering")

        @render.data_frame
        def selected():
            return current_rows().iloc[table.selected_rows()]


# The current (possibly continent-filtered) rows. Positions from
# table.selected_rows() are only meaningful against whatever data frame is
# currently shown, so track it here (ITable.update(df) doesn't expose its
# current data frame for reading it back).
current_rows = reactive.value(countries)


@reactive.effect
def _filter():
    continent = input.continent()
    req(table.widget)
    with reactive.isolate():
        shown = (
            countries
            if continent == "All"
            else countries[countries["continent"] == continent]
        )
        # Positions are into `shown`, so re-map the current selection by a
        # stable key (country name) instead of keeping the old positions,
        # which would now point at different rows (or be out of range).
        kept = set(current_rows().iloc[table.selected_rows()]["country"])
        remapped = [i for i, c in enumerate(shown["country"]) if c in kept]
        table.widget.update(shown, selected_rows=remapped, **TABLE_OPTS)
        current_rows.set(shown)
