# Title: Gapminder 2007: the table is the input
# One-line: A searchable, exportable table drives a highlighted scatter plot and
#     stays filterable by continent without losing its selection.
# Bucket: showcase
# Run: uv run --with plotly shiny run docs/widget-guides/itables/gallery/showcase_gapminder_dashboard.py
# Data: plotly.express.data.gapminder() (142 countries, 2007), ships with plotly.

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
from itables.widget import ITable
from shiny import reactive, req
from shiny.express import input, render, ui
from shinywidgets import render_itables, render_plotly

countries_all = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)
continents = ["All", *sorted(countries_all["continent"].unique())]

# Kept together so the same options can be re-passed to both the initial
# ITable(...) call and every later .update() -- .update(df) alone drops
# columnDefs/buttons unless they're repeated.
TABLE_OPTS = {
    "select": True,
    "buttons": ["copyHtml5", "csvHtml5"],
}

ui.page_opts(title="Gapminder 2007", fillable=True)

with ui.sidebar():
    ui.input_select("continent", "Continent", continents)
    ui.markdown(
        "Search, sort or filter the table; the chart and the summary follow "
        "your selection. Filtering by continent keeps your picks picked."
    )

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("142 countries, 2007")

        @render_itables
        def table():
            return ITable(countries_all, **TABLE_OPTS)

    with ui.card(full_screen=True):
        ui.card_header("Life expectancy vs. GDP per capita")

        @render_plotly
        def scatter():
            fig = go.FigureWidget(
                go.Scatter(
                    x=countries_all["gdpPercap"],
                    y=countries_all["lifeExp"],
                    mode="markers",
                    marker={"color": "#bbb", "size": 8},
                    text=countries_all["country"],
                    hovertemplate="%{text}<extra></extra>",
                )
            )
            fig.update_xaxes(type="log", title="GDP per capita")
            fig.update_yaxes(title="Life expectancy")
            return fig

with ui.card():
    ui.card_header("Selected")

    @render.data_frame
    def selected():
        shown = current_rows()
        return shown.iloc[table.selected_rows()]


# The current (possibly continent-filtered) rows, tracked outside the table
# so other outputs/effects know what the table's positions mean right now
# (ITable.update(df) doesn't expose its current data frame).
current_rows = reactive.value(countries_all)


@reactive.effect
def _filter_by_continent():
    continent = input.continent()
    req(table.widget)
    with reactive.isolate():
        shown = (
            countries_all
            if continent == "All"
            else countries_all[countries_all["continent"] == continent]
        )
        # Re-map the selection by country name: the old row *positions* would
        # otherwise point at different rows (or be out of range) in `shown`.
        kept = set(current_rows().iloc[table.selected_rows()]["country"])
        remapped = [i for i, c in enumerate(shown["country"]) if c in kept]
        table.widget.update(shown, selected_rows=remapped, **TABLE_OPTS)
        current_rows.set(shown)


@reactive.effect
def _highlight_selection():
    shown = current_rows()
    selected_idx = set(table.selected_rows())
    with reactive.isolate():
        colors = ["#e41a1c" if i in selected_idx else "#bbb" for i in range(len(shown))]
        sizes = [12 if i in selected_idx else 8 for i in range(len(shown))]
        # In place: the scatter keeps its zoom/pan state across selections and
        # filters, instead of rebuilding (and resending) the whole figure.
        scatter.widget.data[0].x = shown["gdpPercap"]
        scatter.widget.data[0].y = shown["lifeExp"]
        scatter.widget.data[0].text = shown["country"]
        scatter.widget.data[0].marker.color = colors
        scatter.widget.data[0].marker.size = sizes
