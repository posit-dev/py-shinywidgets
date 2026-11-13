import altair as alt
from altair.datasets import data
from shiny.express import render, ui

from shinywidgets import render_altair

ui.page_opts(title="Reading selected_rows() on demand", fillable=True)

cars = data.cars()

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Drag a box to brush, then download -- no need to click anything first")

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

    with ui.card():

        @render.download_button(
            filename="brushed.csv", label="Download brushed rows as CSV"
        )
        def download():
            # selected_rows() is seeded empty from the moment the chart
            # renders, so this never needs a req() or a prior interaction.
            yield scatter.selected_rows("brush").to_csv(index=False)
