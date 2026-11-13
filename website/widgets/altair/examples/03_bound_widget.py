import altair as alt
from altair.datasets import data
from shiny.express import ui

from shinywidgets import render_altair

ui.page_opts(title="A control built into the chart", fillable=True)

cars = data.cars()


@render_altair
def chart():
    year_slider = alt.binding_range(min=1970, max=1982, step=1, name="Model year: ")
    year = alt.param(name="year", value=1977, bind=year_slider)
    return (
        alt.Chart(cars)
        .mark_circle()
        .encode(
            x="Horsepower:Q",
            y="Miles_per_Gallon:Q",
            color="Origin:N",
            opacity=alt.condition("year(datum.Year) == year", alt.value(0.9), alt.value(0.05)),
        )
        .add_params(year)
    )
