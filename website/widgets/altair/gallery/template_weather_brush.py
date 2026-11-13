# Title: Weather timeline with brush-to-table
# Bucket: template
# One-line: Brush a date range on an Altair timeline and see the matching days
# in a table and two value boxes, computed in Python from the selection.
# Run: uv run --with shinywidgets --with altair shiny run template_weather_brush.py
# Data: altair.datasets' seattle_weather (4 years of real NOAA daily observations).
#
# Note: this header is a comment, not a module docstring -- Shiny Express
# renders a bare top-level string literal as page content.

import altair as alt
from altair.datasets import data
from shiny.express import render, ui

from shinywidgets import render_altair

ui.page_opts(title="Seattle weather", fillable=True)

weather = data.seattle_weather()

with ui.layout_columns(fill=False):
    with ui.value_box():
        "Days selected"

        @render.text
        def n_selected():
            return str(len(timeline.selected_rows("brush")))

    with ui.value_box():
        "Average high"

        @render.text
        def avg_temp():
            rows = timeline.selected_rows("brush")
            return f"{rows['temp_max'].mean():.1f} °C" if len(rows) else "-"

with ui.card(full_screen=True):
    ui.card_header("Drag to brush a date range; double-click to clear")

    @render_altair
    def timeline():
        brush = alt.selection_interval(name="brush", encodings=["x"])
        return (
            alt.Chart(weather)
            .mark_circle()
            .encode(
                x="date:T",
                y="temp_max:Q",
                color=alt.condition(brush, "weather:N", alt.value("lightgray")),
            )
            .add_params(brush)
        )

with ui.card(full_screen=True):
    ui.card_header("Selected days")

    @render.data_frame
    def selected_days():
        return timeline.selected_rows("brush")
