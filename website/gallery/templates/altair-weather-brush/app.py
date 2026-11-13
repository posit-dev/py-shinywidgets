# Title: Weather brush
# Summary: Brush a date range on an Altair timeline and see the matching days
#     in a table and two value boxes, computed in Python from the selection.
# Bucket: template
# Widgets: altair
# Pattern: brushed selection -> table + stats
# Run: uv run shiny run app.py
# Data: altair.datasets' seattle_weather (4 years of real NOAA daily observations)
#
# Source: docs/widget-guides/altair/gallery/template_weather_brush.py

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
