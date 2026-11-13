# Observable Plot: gapminder explorer (showcase)
# A year slider drives a bubble chart in place (no re-render, no re-sent JS
# bundle), and selecting a table row rings the matching bubble.
# Bucket: showcase. Run: shiny run showcase_gapminder_dashboard.py
# Data: plotly.express.data.gapminder() (bundled with plotly).
#
# NOTE: an earlier version of this app also had a second render_obsplot
# output (a life-expectancy histogram) beside the bubble chart. Two
# ObsplotWidget instances mounting at the same time intermittently
# cross-contaminate each other's scales (e.g. the histogram's y-axis would
# pick up the bubble chart's y-domain) -- a pyobsplot/Observable Plot
# concurrency bug, not a shinywidgets one; see NOTES.md. Keeping this
# showcase to a single render_obsplot output avoids it.

from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from pyobsplot import Plot
from shiny.express import input, ui

from shinywidgets import render_itables, render_obsplot

ui.page_opts(title="Gapminder, Observable Plot style", fillable=True)

gapminder = px.data.gapminder()
years = sorted(gapminder["year"].unique().tolist())
cols = ["country", "continent", "lifeExp", "gdpPercap", "pop"]

ui.input_slider(
    "year", "Year", min=years[0], max=years[-1], value=years[-1], step=5, sep=""
)


def year_rows():
    return gapminder[gapminder["year"] == input.year()].reset_index(drop=True)


def bubble_spec(data, highlight: str | None = None) -> dict:
    marks = [
        Plot.dot(
            data,
            {
                "x": "gdpPercap",
                "y": "lifeExp",
                "r": "pop",
                "fill": "continent",
                "fillOpacity": 0.7,
            },
        ),
    ]
    if highlight is not None:
        # reset_index(drop=True): pyobsplot 0.5.4 can't serialize a pandas
        # frame whose index doesn't start at 0 (see Gotchas in guide.md).
        row = data[data["country"] == highlight].reset_index(drop=True)
        if len(row):
            marks.append(
                Plot.dot(
                    row,
                    {
                        "x": "gdpPercap",
                        "y": "lifeExp",
                        "r": "pop",
                        "stroke": "black",
                        "strokeWidth": 2,
                        "fill": "none",
                    },
                )
            )
    return {
        "x": {"type": "log", "label": "GDP per capita"},
        "y": {"domain": [20, 85], "label": "Life expectancy"},
        "r": {"range": [2, 26]},
        "color": {"legend": True},
        "marks": marks,
    }


with ui.card(full_screen=True, height="500px"):
    ui.card_header("GDP per capita vs. life expectancy")

    @render_obsplot
    def bubble():
        data = year_rows()
        rows = table.selected_rows()
        highlight = data.iloc[rows[0]]["country"] if rows else None
        return Plot.plot(bubble_spec(data, highlight))


with ui.card(full_screen=True):
    ui.card_header("Countries this year (select a row to highlight it above)")

    @render_itables
    def table():
        return ITable(year_rows()[cols], select=True, lengthMenu=[5, 10, 25])
