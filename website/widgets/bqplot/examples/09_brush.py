# brush() reports the active brush selector's own region, in data
# coordinates -- not row indices. Use it to filter a data frame yourself.
import bqplot
from bqplot.interacts import BrushIntervalSelector
import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="brush()", fillable=True)

tips = px.data.tips()

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bqplot
        def plot():
            x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
            hist = bqplot.Bins(
                sample=tips["total_bill"],
                scales={"x": x_sc, "y": y_sc},
                colors=["#4c78a8"],
                bins=20,
            )
            return bqplot.Figure(
                marks=[hist],
                axes=[
                    bqplot.Axis(scale=x_sc, label="Total bill ($)"),
                    bqplot.Axis(scale=y_sc, orientation="vertical", label="Count"),
                ],
                interaction=BrushIntervalSelector(scale=x_sc, marks=[hist]),
            )

    with ui.card():
        ui.card_header("Bills in the brushed range")

        @render.code
        def summary():
            region = plot.brush()
            if region is None:
                return "Drag across the histogram to brush a range."
            lo, hi = sorted(region.tolist())
            in_range = tips[tips["total_bill"].between(lo, hi)]
            return (
                f"${lo:.2f}-${hi:.2f}: {len(in_range)} bills, "
                f"average tip ${in_range['tip'].mean():.2f}"
            )
