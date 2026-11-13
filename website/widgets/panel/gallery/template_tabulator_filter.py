# Title: Filterable Panel Tabulator with a linked chart
# Bucket: template
# One-line: Shiny checkboxes filter a Panel Tabulator in place; row selection
#   drives a render_plotly trend chart. A clean starting point for any
#   Panel-table-plus-chart dashboard.
# Run: uv run --no-sync shiny run docs/widget-guides/panel/gallery/template_tabulator_filter.py
# Data: plotly.express.data.gapminder() (ships with plotly)
import pandas as pd
import panel as pn
import plotly.express as px
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_panel, render_plotly

pn.extension("tabulator")

gapminder = px.data.gapminder()
latest = gapminder[gapminder["year"] == 2007]
continents = sorted(latest["continent"].unique().tolist())

ui.page_opts(title="Gapminder explorer", fillable=True)

with ui.sidebar():
    ui.input_checkbox_group(
        "continents", "Continents", continents, selected=continents
    )

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("2007 snapshot (select rows)")

        @render_panel
        def table():
            with reactive.isolate():
                df = latest[latest["continent"].isin(input.continents())]
            return pn.widgets.Tabulator(
                df[["country", "continent", "lifeExp", "pop"]],
                selectable=True, disabled=True, theme="bootstrap5",
                layout="fit_columns", sizing_mode="stretch_both",
                formatters={
                    "lifeExp": {
                        "type": "progress", "min": 40, "max": 85,
                        "color": ["#d7301f", "#fdae61", "#a6d96a", "#1a9850"],
                    }
                },
            )

    with ui.card(full_screen=True):
        ui.card_header("Life expectancy trend")

        @render_plotly
        def trend():
            idx = table.param("selection")
            countries = table.value.value.iloc[idx]["country"].tolist() if idx else []
            df = gapminder[gapminder["country"].isin(countries)] if countries else gapminder.iloc[:0]
            return px.line(df, x="year", y="lifeExp", color="country", markers=True)


@reactive.effect
def _():
    # Rebuild the filtered rows and push them into the table in place, so the
    # user's current sort order survives a continent toggle.
    tab = table.value
    df = latest[latest["continent"].isin(input.continents())][
        ["country", "continent", "lifeExp", "pop"]
    ]
    tab.value = df
