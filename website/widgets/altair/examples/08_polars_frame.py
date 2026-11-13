import altair as alt
from altair.datasets import data
import polars as pl
from shiny.express import render, ui

from shinywidgets import render_altair

ui.page_opts(title="Polars data", fillable=True)

cars = pl.from_pandas(data.cars())

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Chart built from a polars.DataFrame")

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
        ui.card_header("selected_rows() returns a polars.DataFrame")

        @render.code
        def kind():
            return type(scatter.selected_rows("brush")).__name__

        @render.data_frame
        def rows():
            return scatter.selected_rows("brush").select("Name", "Horsepower")
