import altair as alt
from altair.datasets import data
from shiny.express import ui

from shinywidgets import render_altair

ui.page_opts(title="Layers and small multiples", fillable=True)

weather = data.seattle_weather()

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Points layered with a mean rule")

        @render_altair
        def layered():
            points = (
                alt.Chart(weather)
                .mark_circle(opacity=0.4)
                .encode(x="date:T", y="temp_max:Q", color="weather:N")
            )
            mean_rule = alt.Chart(weather).mark_rule(color="black").encode(y="mean(temp_max):Q")
            return points + mean_rule

    with ui.card(full_screen=True):
        ui.card_header("Small multiples with facet()")

        @render_altair
        def faceted():
            return (
                alt.Chart(weather)
                .mark_bar()
                .encode(x="temp_max:Q", y="count()", color="weather:N")
                .properties(width=140, height=120)
                .facet("weather:N", columns=3)
            )
