from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="Update in place", fillable=True)

ui.input_action_button("shrink", "Keep only the 10 most populous")

with ui.card(full_screen=True):

    @render_itables
    def table():
        return ITable(countries, select=True, buttons=["copyHtml5"])


@reactive.effect
@reactive.event(input.shrink)
def _shrink():
    top10 = countries.nlargest(10, "pop")
    # Re-passing `buttons` matters: .update(df) without it silently drops the
    # button row (and any columnDefs) that the original ITable(...) call set.
    table.widget.update(top10, buttons=["copyHtml5"])
