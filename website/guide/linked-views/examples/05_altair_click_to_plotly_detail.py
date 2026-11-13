import altair as alt
from altair.datasets import data
import plotly.graph_objects as go
from shiny.express import render, ui

from shinywidgets import render_altair, render_plotly

cars = data.cars()
avg_hp = cars["Horsepower"].mean()

ui.page_opts(title="Click a car for a detail card", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click a car")

        @render_altair
        def scatter():
            pick = alt.selection_point(name="pick")
            return (
                alt.Chart(cars)
                .mark_circle()
                .encode(
                    x="Horsepower:Q",
                    y="Miles_per_Gallon:Q",
                    color=alt.condition(pick, alt.value("steelblue"), alt.value("lightgray")),
                )
                .add_params(pick)
            )

    with ui.card(full_screen=True):
        ui.card_header("Detail card")

        @render.ui
        def detail():
            rows = scatter.selected_rows("pick")
            if len(rows) == 0:
                return ui.p("Click a car to see its detail.")
            car = rows.iloc[0]
            return ui.TagList(
                ui.h5(car["Name"]),
                ui.p(f"{car['Horsepower']:.0f} hp, {car['Miles_per_Gallon']:.1f} mpg, {car['Origin']}"),
            )

        @render_plotly
        def hp_bar():
            # The detail card's second half is a different library entirely: a
            # small plotly bar comparing the clicked car to the fleet average.
            rows = scatter.selected_rows("pick")
            hp = rows.iloc[0]["Horsepower"] if len(rows) else 0
            colors = ["#e45756", "#bbb"] if len(rows) else ["#eee", "#eee"]
            fig = go.Figure(go.Bar(x=["This car", "Fleet average"], y=[hp, avg_hp], marker_color=colors))
            fig.update_layout(
                title="Horsepower vs. fleet average",
                margin=dict(l=10, r=10, t=40, b=10),
                yaxis_title="Horsepower",
            )
            return fig
