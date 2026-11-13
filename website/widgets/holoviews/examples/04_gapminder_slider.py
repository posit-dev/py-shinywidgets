# The simplest way to drive a plot from a Shiny input: read the input inside
# the render function. Shiny re-runs the function whenever the slider changes,
# and shinywidgets builds a brand-new plot each time (see 07_update_in_place.py
# for a HoloViews DynamicMap that updates the existing plot in place instead).
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny.express import input, render, ui

from shinywidgets import render_holoviews

gapminder = px.data.gapminder()

ui.page_opts(title="Life expectancy vs. GDP per capita", fillable=True)
ui.input_slider("year", "Year", min=1952, max=2007, value=1952, step=5, sep="")


@render_holoviews
def scatter():
    year_df = gapminder[gapminder.year == input.year()]
    return year_df.hvplot.scatter(
        "gdpPercap",
        "lifeExp",
        by="continent",
        logx=True,
        responsive=True,
        size=80,
        alpha=0.7,
        xlim=(200, 120_000),
        ylim=(20, 90),
        title=f"{input.year()}",
    )
