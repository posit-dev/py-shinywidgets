# selected() tracks each mark's selected elements. Click-select needs
# interactions={"click": "select"} -- and that replaces the default hover
# tooltip, so add "hover": "tooltip" back if you still want it.
import bqplot
import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="selected()", fillable=True)

tips = px.data.tips()

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bqplot
        def plot():
            x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
            scatter = bqplot.Scatter(
                x=tips["total_bill"],
                y=tips["tip"],
                scales={"x": x_sc, "y": y_sc},
                colors=["#4c78a8"],
                selected_style={"fill": "#e45756", "stroke": "black"},
                interactions={"click": "select", "hover": "tooltip"},
                tooltip=bqplot.Tooltip(fields=["x", "y"], labels=["bill", "tip"]),
            )
            return bqplot.Figure(
                marks=[scatter],
                axes=[
                    bqplot.Axis(scale=x_sc, label="Total bill ($)"),
                    bqplot.Axis(scale=y_sc, orientation="vertical", label="Tip ($)"),
                ],
            )

    with ui.card():
        ui.card_header("Selected row")

        @render.data_frame
        def detail():
            # empty while nothing is selected; the figure has one mark, so
            # mark= can be omitted
            return plot.selected_rows(tips)
