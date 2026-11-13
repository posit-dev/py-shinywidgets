from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="Select from Python", fillable=True)

ui.input_action_button("top5", "Select the 5 most populous")

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_itables
        def table():
            return ITable(countries, select=True)

    with ui.card():
        ui.card_header("Selected")

        @render.data_frame
        def selected():
            return countries.iloc[table.selected_rows()]


@reactive.effect
@reactive.event(input.top5)
def _select_top5():
    # Setting .selected_rows on the widget highlights those rows in the
    # browser immediately, exactly as if the user had clicked them -- no
    # re-render, so sort/search/scroll state is untouched.
    top5 = countries.nlargest(5, "pop").index.tolist()
    table.widget.selected_rows = top5
