import altair as alt
from altair.datasets import data
from shiny.express import render, ui

from shinywidgets import render_altair

ui.page_opts(title="Binned and temporal fields", fillable=True)

cars = data.cars()

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Click a bar: binned selection")

        @render_altair
        def histogram():
            pick = alt.selection_point(name="hp_bin", encodings=["x"])
            return (
                alt.Chart(cars)
                .mark_bar()
                .encode(
                    x=alt.X("Horsepower:Q", bin=alt.Bin(step=25)),
                    y="count()",
                    color=alt.condition(pick, alt.value("steelblue"), alt.value("lightgray")),
                )
                .add_params(pick)
            )

        @render.text
        def bin_count():
            n = len(histogram.selected_rows("hp_bin"))
            return f"{n} cars in the selected 25-hp bin" if n else "Click a bar above"

    with ui.card(full_screen=True):
        ui.card_header("Drag along the axis: temporal interval")

        @render_altair
        def timeline():
            brush = alt.selection_interval(name="years", encodings=["x"])
            return (
                alt.Chart(cars)
                .mark_tick()
                .encode(x="Year:T")
                .add_params(brush)
            )

        @render.text
        def year_count():
            n = len(timeline.selected_rows("years"))
            return f"{n} cars in the selected years" if n else "Drag along the axis above"
