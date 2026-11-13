# Title: Gapminder explorer
# Bucket: showcase
# Description: A Python-animated bubble chart (play the year slider -- no
#     plotly frames involved), linked to a 142-country trend chart that
#     highlights in place when you lasso bubbles, plus a click-through detail
#     card and a dark-mode toggle. Demonstrates batch_animate, the clicked()/
#     selected() accessors, and in-place cross-chart highlighting.
# Run: uv run --no-sync shiny run docs/widget-guides/plotly/gallery/showcase_gapminder_explorer.py
# Data: plotly.express.data.gapminder() (ships with plotly)

import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_plotly

df = px.data.gapminder()
years = sorted(df["year"].unique())
countries = sorted(df["country"].unique())
continents = sorted(df["continent"].unique())
by_year = {y: df[df["year"] == y].set_index("country") for y in years}
CONTINENT_COLORS = dict(zip(continents, px.colors.qualitative.Plotly))
MARGIN = dict(l=16, r=16, t=32, b=16)

ui.page_opts(title="Gapminder explorer", fillable=True)

with ui.sidebar(width=240):
    ui.input_dark_mode(id="mode")
    ui.input_slider(
        "year",
        "Year",
        years[0],
        years[-1],
        years[0],
        step=5,
        sep="",
        animate=ui.AnimationOptions(interval=900, loop=True),
    )
    "Lasso bubbles to trace their history on the right."

with ui.layout_columns(col_widths=[7, 5, 12]):
    with ui.card(full_screen=True):
        ui.card_header("Life expectancy vs. GDP per capita")

        @render_plotly
        def bubbles():
            d = by_year[years[0]].reset_index()
            fig = px.scatter(
                d,
                x="gdpPercap",
                y="lifeExp",
                size="pop",
                color="continent",
                color_discrete_map=CONTINENT_COLORS,
                category_orders={"continent": continents},
                log_x=True,
                size_max=60,
                range_x=[200, 60000],
                range_y=[20, 90],
                custom_data=["country"],
            )
            fig.update_layout(dragmode="lasso", margin=MARGIN)
            return fig

    with ui.card():
        ui.card_header("Click a bubble")

        @render.ui
        def detail():
            pts = bubbles.clicked()
            if pts is None:
                return ui.p("Click a bubble for details.", class_="text-muted")
            country = pts["customdata"].iloc[0][0]
            row = by_year[input.year()].loc[country]
            return ui.TagList(
                ui.h4(f"{country} ({input.year()})"),
                ui.p(f"Continent: {row['continent']}"),
                ui.p(f"Life expectancy: {row['lifeExp']:.1f} years"),
                ui.p(f"GDP per capita: ${row['gdpPercap']:,.0f}"),
                ui.p(f"Population: {row['pop']:,}"),
            )

    with ui.card(full_screen=True):
        ui.card_header("Life expectancy, 1952-2007")

        @render_plotly
        def trends():
            fig = go.Figure()
            for country in countries:
                d = df[df["country"] == country]
                fig.add_scatter(
                    x=d["year"],
                    y=d["lifeExp"],
                    mode="lines",
                    name=country,
                    line=dict(color="rgba(140, 140, 140, 0.25)", width=1),
                    showlegend=False,
                    hoverinfo="skip",
                )
            fig.update_layout(yaxis_title="lifeExp", margin=MARGIN)
            return fig


# Advance the bubbles with a tween instead of rebuilding the chart: a
# re-render would reset the lasso selection and the zoom on every year.
@reactive.effect
def _animate():
    d = by_year[input.year()].reset_index()
    with bubbles.widget.batch_animate(duration=700, easing="cubic-in-out"):
        for trace in bubbles.widget.data:
            sub = d[d["continent"] == trace.name]
            trace.x, trace.y, trace.marker.size = (
                sub["gdpPercap"],
                sub["lifeExp"],
                sub["pop"],
            )
            trace.customdata = [[c] for c in sub["country"]]


# Highlight the lassoed countries in the trend chart without rebuilding it:
# restyling 142 traces in place is one message and keeps their hover state.
@reactive.effect
def _highlight():
    pts = bubbles.selected()
    selected = set() if pts is None else {c[0] for c in pts["customdata"]}
    with trends.widget.batch_update():
        for trace in trends.widget.data:
            on = trace.name in selected
            trace.line.color = "#1f77b4" if on else "rgba(140, 140, 140, 0.15)"
            trace.line.width = 2.5 if on else 1


# A template swap preserves explicitly-set margins, but MARGIN is passed
# again anyway since it costs nothing and keeps this effect self-contained.
@reactive.effect
def _theme():
    template = "plotly_dark" if input.mode() == "dark" else "plotly_white"
    for fig in (bubbles.widget, trends.widget):
        fig.update_layout(
            template=template,
            margin=MARGIN,
            paper_bgcolor="rgba(0, 0, 0, 0)",
            plot_bgcolor="rgba(0, 0, 0, 0)",
        )
