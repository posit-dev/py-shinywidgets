# Pattern: widget state -> another widget updated in place. bqplot's own
# selectors can only highlight marks on the figure they're attached to, so
# linking a *second* figure goes through Python: read selected() here, set
# .selected on the other figure's mark in an effect. No re-render either side.
import bqplot
import bqplot.interacts as interacts
import plotly.express as px
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="Linked brushing", fillable=True)

gap2007 = px.data.gapminder().query("year == 2007").reset_index(drop=True)
gdp_sc, life_sc, pop_sc = bqplot.LogScale(), bqplot.LinearScale(), bqplot.LogScale()

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("GDP vs life expectancy (brush here)")

        @render_bqplot
        def left():
            wealth = bqplot.Scatter(
                x=gap2007["gdpPercap"],
                y=gap2007["lifeExp"],
                scales={"x": gdp_sc, "y": life_sc},
                colors=["#4c78a8"],
                selected_style={"fill": "#e45756"},
                unselected_style={"opacity": 0.3},
            )
            return bqplot.Figure(
                marks=[wealth],
                axes=[bqplot.Axis(scale=gdp_sc), bqplot.Axis(scale=life_sc, orientation="vertical")],
                interaction=interacts.BrushSelector(x_scale=gdp_sc, y_scale=life_sc, marks=[wealth]),
            )

    with ui.card(full_screen=True):
        ui.card_header("Population vs life expectancy (same countries highlight)")

        @render_bqplot
        def right():
            by_pop = bqplot.Scatter(
                x=gap2007["pop"],
                y=gap2007["lifeExp"],
                scales={"x": pop_sc, "y": life_sc},
                colors=["#4c78a8"],
                selected_style={"fill": "#e45756"},
                unselected_style={"opacity": 0.3},
            )
            return bqplot.Figure(
                marks=[by_pop],
                axes=[bqplot.Axis(scale=pop_sc), bqplot.Axis(scale=life_sc, orientation="vertical")],
            )


with ui.card():

    @render.code
    def count():
        sel = left.selected()[0]
        return "no countries brushed" if sel is None else f"{len(sel)} countries"


@reactive.effect
def _highlight_right():
    sel = left.selected()[0]
    with reactive.isolate():
        by_pop = right.widget.marks[0]
    by_pop.selected = sel
