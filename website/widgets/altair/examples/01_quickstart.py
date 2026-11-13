import altair as alt
from altair.datasets import data
from shiny.express import ui

from shinywidgets import render_altair

ui.page_opts(title="Cars", fillable=True)

cars = data.cars()


@render_altair
def plot():
    return (
        alt.Chart(cars)
        .mark_circle()
        .encode(x="Horsepower:Q", y="Miles_per_Gallon:Q", color="Origin:N")
    )
