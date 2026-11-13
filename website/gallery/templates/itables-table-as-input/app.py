# Title: Table as input
# Summary: A searchable, sortable, exportable table whose selection drives a
#     summary panel.
# Bucket: template
# Widgets: itables
# Pattern: selection -> summary
# Run: uv run shiny run app.py
# Data: plotly.express.data.gapminder() (142 countries, 2007), ships with plotly
#
# Adapt this by swapping `countries` for your own data frame and `summary()`
# for whatever the selection should drive (a plot, a download, a model run).
#
# Source: docs/widget-guides/itables/gallery/template_table_as_input.py

from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny.express import render, ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="Table as input", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Click rows to select them (Ctrl/Cmd-click for several)")

        @render_itables
        def table():
            return ITable(
                countries,
                select=True,
                buttons=["copyHtml5", "csvHtml5"],
                column_filters="header",
            )

    with ui.card():
        ui.card_header("Selection summary")

        @render.ui
        def summary():
            rows = table.selected_rows()
            subset = countries.iloc[rows] if rows else countries
            label = f"{len(rows)} selected" if rows else "All 142 countries"
            return ui.TagList(
                ui.h5(label),
                ui.p(f"Mean life expectancy: {subset['lifeExp'].mean():.1f} years"),
                ui.p(f"Total population: {subset['pop'].sum():,}"),
            )
