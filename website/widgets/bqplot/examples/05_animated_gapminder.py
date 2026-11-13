# bqplot's signature move: set Figure.animation_duration once, then mutate a
# mark's data in an effect. bqplot tweens the points to their new positions
# instead of redrawing, so the slider feels like it's scrubbing through time.
import bqplot
import plotly.express as px
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="Animated gapminder", fillable=True)

gap = px.data.gapminder()
years = sorted(int(y) for y in gap["year"].unique())
continents = sorted(gap["continent"].unique())

ui.input_slider("year", "Year", min(years), max(years), min(years), step=5, sep="")

with ui.card(full_screen=True):

    @render_bqplot
    def bubbles():
        x_sc = bqplot.LogScale(min=200, max=1e5)
        y_sc = bqplot.LinearScale(min=20, max=90)
        c_sc = bqplot.OrdinalColorScale(domain=continents, scheme="Set1")
        size_sc = bqplot.LinearScale(min=0.0, max=float(gap["pop"].max()))

        points = bqplot.Scatter(
            scales={"x": x_sc, "y": y_sc, "color": c_sc, "size": size_sc},
            default_size=3000,
            default_opacities=[0.7],
            stroke="white",
        )
        fig = bqplot.Figure(
            marks=[points],
            axes=[
                bqplot.Axis(scale=x_sc, label="GDP per capita"),
                bqplot.Axis(scale=y_sc, orientation="vertical", label="Life expectancy"),
            ],
            title="Gapminder",
            animation_duration=750,
        )
        return fig

    @reactive.effect
    def _update_year():
        year_data = gap[gap["year"] == input.year()]
        points = bubbles.widget.marks[0]
        # Setting several traits inside one hold_sync() batches them into a
        # single update message, so the browser doesn't tween x, then y, then
        # size as three separate steps
        with points.hold_sync():
            points.x = year_data["gdpPercap"].to_numpy()
            points.y = year_data["lifeExp"].to_numpy()
            points.color = year_data["continent"].to_numpy()
            points.size = year_data["pop"].to_numpy()
