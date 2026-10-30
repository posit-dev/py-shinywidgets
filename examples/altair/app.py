import altair as alt
import shiny.express
from shiny import render
from vega_datasets import data

from shinywidgets import render_altair

cars = data.cars()


# Replicate JupyterChart interactivity
# https://altair-viz.github.io/user_guide/jupyter_chart.html#point-selections
@render_altair
def jchart():
    brush = alt.selection_point(name="point", encodings=["color"], bind="legend")
    return alt.Chart(cars).mark_point().encode(
        x='Horsepower:Q',
        y='Miles_per_Gallon:Q',
        color=alt.condition(brush, 'Origin:N', alt.value('grey')),
    ).add_params(brush)


# Output selection information (click on legend in the plot)
@render.code
def selection():
    return "Selected point: " + str(jchart.selected("point").value)


@render.data_frame
def selected_cars():
    return jchart.selected_rows("point")
