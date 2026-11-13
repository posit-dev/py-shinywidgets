# title: Brush explorer
# description: Brush a scatter plot and read the selected rows back into a
#   table and a summary -- a clean starting point for "select to filter" apps.
# bucket: template
# run: uv run --with shinywidgets[bqplot] --with plotly shiny run template_brush_explorer.py
# data: plotly.express.data.tips() (ships with plotly)
import bqplot
import bqplot.interacts as interacts
import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="Brush explorer", fillable=True)

tips = px.data.tips()

with ui.layout_sidebar():
    with ui.sidebar(width=320):
        ui.p("Drag a box over the plot to brush restaurant visits.")

        @render.code
        def summary():
            rows = plot.selected_rows(tips)
            if len(rows) == 0:
                return "No visits brushed."
            return (
                f"{len(rows)} visits\n"
                f"avg bill: ${rows['total_bill'].mean():.2f}\n"
                f"avg tip:  ${rows['tip'].mean():.2f}"
            )

        @render.data_frame
        def table():
            cols = ["day", "time", "size", "total_bill", "tip"]
            return plot.selected_rows(tips)[cols]

    with ui.card(full_screen=True):

        @render_bqplot
        def plot():
            x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
            scatter = bqplot.Scatter(
                x=tips["total_bill"],
                y=tips["tip"],
                scales={"x": x_sc, "y": y_sc},
                colors=["#4c78a8"],
                selected_style={"fill": "#e45756"},
                unselected_style={"opacity": 0.3},
            )
            return bqplot.Figure(
                marks=[scatter],
                axes=[
                    bqplot.Axis(scale=x_sc, label="Total bill ($)"),
                    bqplot.Axis(scale=y_sc, orientation="vertical", label="Tip ($)"),
                ],
                interaction=interacts.BrushSelector(
                    x_scale=x_sc, y_scale=y_sc, marks=[scatter]
                ),
            )
