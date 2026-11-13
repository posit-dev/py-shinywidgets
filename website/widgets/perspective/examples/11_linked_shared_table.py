from __future__ import annotations

import plotly.express as px
from perspective import Server
from perspective.widget import PerspectiveWidget
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_perspective

ui.page_opts(title="One table, two views", fillable=True)
ui.input_action_button("revise", "Apply revised population estimates")

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])

# Express re-runs this whole script once per session, so a table built here
# at the top level is already private to this session -- no extra bookkeeping
# needed to share it between the two viewers below. `index="country"` makes
# update() upsert: matching rows are revised in place instead of appended.
table = Server().new_local_client().table(countries, index="country")


@reactive.effect
@reactive.event(input.revise)
def _():
    # A real-world update: a few countries get revised population figures.
    # Streams to both viewers below at once -- they share one table.
    table.update(
        [
            {"country": "China", "pop": 1_360_000_000},
            {"country": "India", "pop": 1_200_000_000},
            {"country": "Nigeria", "pop": 150_000_000},
        ]
    )


with ui.layout_columns():

    @render_perspective
    def datagrid():
        return PerspectiveWidget(table, plugin="Datagrid")

    @render_perspective
    def treemap():
        return PerspectiveWidget(
            table,
            plugin="Treemap",
            columns=["pop"],  # otherwise sizes by the auto "index" column
            group_by=["continent", "country"],
            aggregates={"pop": "sum"},
        )
