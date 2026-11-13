import altair as alt
from altair.datasets import data
from reactable import Reactable
from shiny.express import ui

from shinywidgets import render_altair, render_reactable

ui.page_opts(title="Brush an altair chart, render a reactable table", fillable=True)

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
        ui.card_header("Selected rows, as a reactable table")

        @render_reactable
        def tbl():
            # reactable reads its data once per render, so a new selection
            # means a new table rather than an in-place update.
            rows = scatter.selected_rows("brush")[["Name", "Horsepower", "Miles_per_Gallon"]]
            return Reactable(rows, default_page_size=6)
