import altair as alt
from altair.datasets import data
from shiny.express import render, ui

from shinywidgets import reactive_read, render_altair

ui.page_opts(title="Reading a bound param with reactive_read", fillable=True)

cars = data.cars()

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Model year is a param, not a selection")

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
                    opacity=alt.condition(
                        "year(datum.Year) == year", alt.value(0.9), alt.value(0.05)
                    ),
                )
                .add_params(year)
            )

    with ui.card(full_screen=True):
        ui.card_header("Python reacts to the slider too")

        @render.text
        def year_value():
            # params aren't selections, so there's no accessor for them;
            # reactive_read watches the trait directly.
            year = reactive_read(chart.widget.params, "year")
            return f"Showing model year {int(year)}" if year is not None else "..."
