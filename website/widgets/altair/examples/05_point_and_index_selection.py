import altair as alt
from altair.datasets import data
from shiny.express import render, ui

from shinywidgets import render_altair

ui.page_opts(title="Point selections: legend vs. mark clicks", fillable=True)

cars = data.cars()

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("encodings=['color']: click a legend entry")

        @render_altair(height="320px")
        def by_legend():
            pick = alt.selection_point(name="origin_pick", encodings=["color"], bind="legend")
            return (
                alt.Chart(cars)
                .mark_circle()
                .encode(
                    x="Horsepower:Q",
                    y="Miles_per_Gallon:Q",
                    color=alt.condition(pick, "Origin:N", alt.value("lightgray")),
                )
                .add_params(pick)
            )

        @render.code
        def legend_value():
            return str(by_legend.selected("origin_pick").value)

    with ui.card(full_screen=True):
        ui.card_header("No encodings/fields: shift-click points")

        @render_altair(height="320px")
        def by_mark():
            pick = alt.selection_point(name="car_pick")
            return (
                alt.Chart(cars)
                .mark_circle()
                .encode(
                    x="Horsepower:Q",
                    y="Miles_per_Gallon:Q",
                    color=alt.condition(pick, alt.value("steelblue"), alt.value("lightgray")),
                )
                .add_params(pick)
            )

        @render.text
        def picked_count():
            return f"{len(by_mark.selected_rows('car_pick'))} cars picked (row positions: {by_mark.selected('car_pick').value})"

        @render.data_frame
        def picked_cars():
            return by_mark.selected_rows("car_pick")[["Name", "Horsepower"]]
