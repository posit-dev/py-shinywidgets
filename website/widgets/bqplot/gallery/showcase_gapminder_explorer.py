# title: Gapminder explorer
# description: An animated, Hans Rosling-style bubble chart with play/pause,
#   lasso selection, and a ranked bar chart of the lassoed countries that
#   updates in place.
# bucket: showcase
# run: uv run --with shinywidgets[bqplot] --with plotly shiny run showcase_gapminder_explorer.py
# data: plotly.express.data.gapminder() (ships with plotly)
from __future__ import annotations

import bqplot
import bqplot.interacts as interacts
import plotly.express as px
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_bqplot

ui.page_opts(title="Gapminder explorer", fillable=True)

gap = px.data.gapminder()
years = sorted(int(y) for y in gap["year"].unique())
continents = sorted(gap["continent"].unique())
COLORS = {
    "Africa": "#4c78a8",
    "Americas": "#f58518",
    "Asia": "#54a24b",
    "Europe": "#e45756",
    "Oceania": "#b279a2",
}

with ui.layout_columns(col_widths=[3, 9]):
    with ui.card():
        ui.card_header("Controls")
        ui.input_slider("year", "Year", min(years), max(years), min(years), step=5, sep="")
        ui.input_action_button("play", "Play / Pause", class_="mb-2")
        ui.p(
            "Lasso a group of bubbles to rank them by population on the right.",
            class_="text-muted small",
        )

        @render.code
        def selection_summary():
            rows = bubbles.selected_rows(year_rows())
            if len(rows) == 0:
                return "No countries selected."
            return f"{len(rows)} countries, {rows['pop'].sum() / 1e6:.0f}M people"

    with ui.layout_columns(col_widths=[7, 5]):
        with ui.card(full_screen=True):
            ui.card_header("Life expectancy vs GDP per capita")

            @render_bqplot
            def bubbles():
                x_sc = bqplot.LogScale(min=200, max=1.2e5)
                y_sc = bqplot.LinearScale(min=20, max=90)
                size_sc = bqplot.LinearScale(min=0.0, max=float(gap["pop"].max()))
                c_sc = bqplot.OrdinalColorScale(
                    domain=continents, colors=[COLORS[c] for c in continents]
                )
                points = bqplot.Scatter(
                    scales={"x": x_sc, "y": y_sc, "size": size_sc, "color": c_sc},
                    default_size=2200,
                    default_opacities=[0.75],
                    stroke="white",
                    selected_style={"stroke": "black", "stroke-width": 2},
                    unselected_style={"opacity": 0.2},
                )
                fig = bqplot.Figure(
                    marks=[points],
                    axes=[
                        bqplot.Axis(scale=x_sc, label="GDP per capita"),
                        bqplot.Axis(scale=y_sc, orientation="vertical", label="Life expectancy"),
                    ],
                    animation_duration=600,
                    interaction=interacts.LassoSelector(
                        x_scale=x_sc, y_scale=y_sc, marks=[points]
                    ),
                )
                return fig

        with ui.card(full_screen=True):
            ui.card_header("Selected countries, by population")

            @render_bqplot
            def ranked():
                x_sc, y_sc = bqplot.OrdinalScale(), bqplot.LinearScale(min=0, max=1)
                bars = bqplot.Bars(
                    x=[], y=[], scales={"x": x_sc, "y": y_sc}, colors=["#4c78a8"]
                )
                return bqplot.Figure(
                    marks=[bars],
                    axes=[
                        bqplot.Axis(scale=x_sc, tick_rotate=-45),
                        bqplot.Axis(scale=y_sc, orientation="vertical", label="Population (M)"),
                    ],
                    animation_duration=500,
                )


def year_rows():
    return gap[gap["year"] == input.year()].reset_index(drop=True)


@reactive.effect
def _update_bubbles():
    rows = year_rows()
    points = bubbles.widget.marks[0]
    with points.hold_sync():
        points.x = rows["gdpPercap"].to_numpy()
        points.y = rows["lifeExp"].to_numpy()
        points.color = rows["continent"].to_numpy()
        points.size = rows["pop"].to_numpy()


@reactive.effect
def _update_ranked():
    rows = year_rows()
    selected = bubbles.selected_rows(rows)
    top = selected.nlargest(8, "pop") if len(selected) > 0 else rows.nlargest(8, "pop")
    bars = ranked.widget.marks[0]
    y_sc = bars.scales["y"]
    with reactive.isolate():
        y_sc.max = float(top["pop"].max() / 1e6) * 1.1
    with bars.hold_sync():
        bars.x = top["country"].to_numpy()
        bars.y = (top["pop"] / 1e6).to_numpy()


playing = reactive.value(False)


@reactive.effect
@reactive.event(input.play)
def _toggle_play():
    playing.set(not playing.get())


@reactive.effect
def _advance_year():
    if not playing.get():
        return
    reactive.invalidate_later(1.2)
    with reactive.isolate():
        i = years.index(input.year())
    next_year = years[(i + 1) % len(years)]
    ui.update_slider("year", value=next_year)
