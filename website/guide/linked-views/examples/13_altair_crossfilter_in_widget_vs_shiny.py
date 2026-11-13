import altair as alt
from altair.datasets import data
from shiny.express import render, ui

from shinywidgets import render_altair

ui.page_opts(title="Two ways to link a selection", fillable=True)

cars = data.cars()

with ui.card(full_screen=True):
    ui.card_header("Brush the scatter plot")

    @render_altair
    def chart():
        brush = alt.selection_interval(name="brush", encodings=["x"])
        top = (
            alt.Chart(cars)
            .mark_point()
            .encode(x="Horsepower:Q", y="Miles_per_Gallon:Q")
            .properties(height=260)
            .add_params(brush)
        )
        # Filtered entirely inside Vega-Lite: no Python round trip, updates
        # on every mouse-move while dragging.
        bottom = (
            alt.Chart(cars)
            .mark_bar()
            .encode(x="Origin:N", y="count()")
            .properties(height=140)
            .transform_filter(brush)
        )
        return top & bottom

with ui.card():
    ui.card_header("Through Shiny: a stat Vega-Lite's grammar can't compute")

    @render.text
    def summary():
        rows = chart.selected_rows("brush")
        if len(rows) == 0:
            return "Brush the scatter plot above to select cars."
        return f"{len(rows)} selected, average {rows['Miles_per_Gallon'].mean():.1f} mpg"
