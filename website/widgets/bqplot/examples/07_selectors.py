# Seven interaction selectors share the same trait, fig.interaction, so
# swapping tools is one assignment -- no re-render, selected() picks up the
# new selector automatically.
import bqplot
import bqplot.interacts as interacts
import plotly.express as px
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="Selectors", fillable=True)

iris = px.data.iris()
x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
scatter = bqplot.Scatter(
    x=iris["sepal_length"],
    y=iris["petal_length"],
    scales={"x": x_sc, "y": y_sc},
    colors=["#4c78a8"],
    selected_style={"fill": "#e45756", "stroke": "black"},
)

ui.input_radio_buttons(
    "tool", "Selector", ["Brush", "Lasso", "Index"], inline=True
)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bqplot
        def plot():
            return bqplot.Figure(
                marks=[scatter],
                axes=[bqplot.Axis(scale=x_sc), bqplot.Axis(scale=y_sc, orientation="vertical")],
                interaction=interacts.BrushSelector(
                    x_scale=x_sc, y_scale=y_sc, marks=[scatter]
                ),
            )

    with ui.card():
        ui.card_header("Selected rows")

        @render.code
        def n_selected():
            sel = plot.selected()[0]
            return "none" if sel is None else f"{len(sel)} point(s)"


@reactive.effect
def _swap_selector():
    tool = input.tool()
    if tool == "Brush":
        new = interacts.BrushSelector(x_scale=x_sc, y_scale=y_sc, marks=[scatter])
    elif tool == "Lasso":
        new = interacts.LassoSelector(x_scale=x_sc, y_scale=y_sc, marks=[scatter])
    else:
        new = interacts.IndexSelector(scale=x_sc, marks=[scatter])
    plot.widget.interaction = new
