import altair as alt
from altair.datasets import data
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_altair

ui.page_opts(title="Updating a param in place", fillable=True)

cars = data.cars()

with ui.sidebar():
    ui.input_slider("threshold", "Highlight above (mpg)", min=10, max=45, value=30)

with ui.card(full_screen=True):
    ui.card_header("Moving the slider restyles the chart without resending data")

    @render_altair
    def chart():
        with reactive.isolate():
            threshold = alt.param(name="threshold", value=input.threshold())
        return (
            alt.Chart(cars)
            .mark_circle()
            .encode(
                x="Horsepower:Q",
                y="Miles_per_Gallon:Q",
                color=alt.condition(
                    "datum.Miles_per_Gallon > threshold", alt.value("crimson"), alt.value("lightgray")
                ),
            )
            .add_params(threshold)
        )

    @reactive.effect
    def _():
        chart.widget.params.threshold = input.threshold()
