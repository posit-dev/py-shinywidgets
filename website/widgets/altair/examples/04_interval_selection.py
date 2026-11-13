import altair as alt
from altair.datasets import data
from shiny.express import render, ui

from shinywidgets import render_altair

ui.page_opts(title="Interval (brush) selection", fillable=True)

cars = data.cars()

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Drag a box to brush")

        @render_altair
        def scatter():
            brush = alt.selection_interval(name="brush")
            return (
                alt.Chart(cars)
                .mark_circle()
                .encode(
                    x="Horsepower:Q",
                    y="Miles_per_Gallon:Q",
                    color=alt.condition(brush, "Origin:N", alt.value("lightgray")),
                )
                .add_params(brush)
            )

    with ui.card(full_screen=True):
        ui.card_header("Rows inside the brush")

        @render.data_frame
        def brushed():
            return scatter.selected_rows("brush")[["Name", "Horsepower", "Miles_per_Gallon"]]
