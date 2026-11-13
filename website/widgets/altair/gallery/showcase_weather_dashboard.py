# Title: Four years of weather: brush, restyle, and summarize
# Bucket: showcase
# One-line: A brushable, four-year weather timeline that restyles in place as you
# move a threshold slider, and whose brushed selection drives a Python-computed
# comparison chart and summary stats -- all from two accessors.
# Run: uv run --with shinywidgets --with altair shiny run showcase_weather_dashboard.py
# Data: altair.datasets' seattle_weather (4 years of real NOAA daily observations).
#
# Note: this header is a comment, not a module docstring -- Shiny Express
# renders a bare top-level string literal as page content.

import altair as alt
from altair.datasets import data
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_altair

ui.page_opts(title="Four years of Seattle weather", fillable=True)

df = data.seattle_weather()
WEATHER = ["sun", "fog", "drizzle", "rain", "snow"]
COLORS = ["#e7ba52", "#a7a7a7", "#aec7e8", "#1f77b4", "#9467bd"]

with ui.sidebar(width=290):
    ui.input_slider("hot", "Hot-day threshold (C)", 15, 30, 24)
    ui.input_checkbox_group("types", "Weather", WEATHER, selected=WEATHER, inline=True)
    ui.markdown(
        "**Drag** across the timeline to brush a date range; **double-click** to "
        "clear. The slider restyles the chart *in place* (a small param update, "
        "no data resent). The weather checkboxes re-render (they change what "
        "data the chart holds). Everything below the chart is computed in "
        "Python from `timeline.selected_rows()`."
    )


def shown() -> pd.DataFrame:
    return df[df["weather"].isin(input.types())]


@reactive.calc
def brushed() -> pd.DataFrame:
    # `timeline` layers two `alt.Chart(...)` calls; altair only hoists a
    # layered chart's data to the top level when every layer was built from
    # the *same* data frame object (by identity, not equality), so pass `df=`
    # explicitly rather than relying on `selected_rows()` to find one.
    return timeline.selected_rows("brush", df=shown())


with ui.layout_columns(fill=False):
    with ui.value_box():
        "Days selected"

        @render.text
        def n_selected():
            return str(len(brushed()))

    with ui.value_box():
        "Average high"

        @render.text
        def avg_temp():
            rows = brushed()
            return f"{rows['temp_max'].mean():.1f} C" if len(rows) else "-"

    with ui.value_box():
        "Date range"

        @render.text
        def date_range():
            rows = brushed()
            if len(rows) == 0:
                return "none"
            return f"{rows['date'].min():%Y-%m-%d} to {rows['date'].max():%Y-%m-%d}"


with ui.card(full_screen=True):
    ui.card_header("Drag to brush; the threshold line and dot colors update live")

    @render_altair
    def timeline():
        brush = alt.selection_interval(name="brush", encodings=["x"])
        with reactive.isolate():
            hot = alt.param(name="hot", value=input.hot())
        data = shown()
        points = (
            alt.Chart(data)
            .mark_circle(opacity=0.6)
            .encode(
                x="date:T",
                y="temp_max:Q",
                color=alt.Color("weather:N", scale=alt.Scale(domain=WEATHER, range=COLORS)),
                opacity=alt.condition(brush, alt.value(0.8), alt.value(0.15)),
            )
            .add_params(brush, hot)
        )
        rule = alt.Chart(data).mark_rule(color="crimson", strokeDash=[4, 4]).encode(
            y="hot:Q"
        ).transform_calculate(hot="hot")
        return points + rule

    @reactive.effect
    def _():
        timeline.widget.params.hot = input.hot()


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Selected days vs. all days, by weather")

        @render_altair
        def comparison():
            rows = brushed()
            if len(rows) == 0:
                counts = pd.DataFrame({"weather": [], "group": [], "n": []})
            else:
                sel = rows["weather"].value_counts().rename_axis("weather").reset_index(name="n")
                sel["group"] = "selected"
                all_ = shown()["weather"].value_counts().rename_axis("weather").reset_index(name="n")
                all_["group"] = "all shown"
                counts = pd.concat([sel, all_])
            return (
                alt.Chart(counts)
                .mark_bar()
                .encode(
                    x="group:N",
                    xOffset="group:N",
                    y="n:Q",
                    color=alt.Color("weather:N", scale=alt.Scale(domain=WEATHER, range=COLORS)),
                )
            )

    with ui.card(full_screen=True):
        ui.card_header("Hottest selected days")

        @render.data_frame
        def hottest():
            return brushed().nlargest(10, "temp_max")[["date", "temp_max", "weather"]]
