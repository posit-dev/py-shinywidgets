import altair as alt
from altair.datasets import data
from shiny.express import render, ui

from shinywidgets import render_altair

ui.page_opts(title="Two named selections on one chart", fillable=True)

cars = data.cars()


@render_altair
def chart():
    brush = alt.selection_interval(name="brush", encodings=["x"])
    origin_pick = alt.selection_point(name="origin_pick", encodings=["color"], bind="legend")
    return (
        alt.Chart(cars)
        .mark_circle()
        .encode(
            x="Horsepower:Q",
            y="Miles_per_Gallon:Q",
            color=alt.condition(origin_pick, "Origin:N", alt.value("lightgray")),
            opacity=alt.condition(brush, alt.value(1.0), alt.value(0.3)),
        )
        .add_params(brush, origin_pick)
    )


with ui.layout_columns():

    @render.code
    def brush_state():
        return f"brush: {chart.selected('brush').value}"

    @render.code
    def legend_state():
        return f"origin_pick: {chart.selected('origin_pick').value}"
