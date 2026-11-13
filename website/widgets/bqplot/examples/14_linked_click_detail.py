# Pattern: click a point -> detail card. A single-click selection is one row
# of selected_rows(), so the same accessor drives a 1-row detail view.
import bqplot
import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="Click to detail", fillable=True)

tips = px.data.tips()

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click a table visit")

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
            )
            return bqplot.Figure(
                marks=[scatter],
                axes=[
                    bqplot.Axis(scale=x_sc, label="Total bill ($)"),
                    bqplot.Axis(scale=y_sc, orientation="vertical", label="Tip ($)"),
                ],
            )

    with ui.card():
        ui.card_header("Visit detail")

        @render.ui
        def detail():
            rows = plot.selected_rows(tips)
            if len(rows) == 0:
                return ui.p("Click a point to see its details.")
            row = rows.iloc[0]  # a click selects a single visit
            pct = 100 * row["tip"] / row["total_bill"]
            return ui.TagList(
                ui.h5(f"{row['day']} {row['time']}"),
                ui.p(f"Party of {row['size']}, bill ${row['total_bill']:.2f}"),
                ui.p(f"Tip ${row['tip']:.2f} ({pct:.0f}%)"),
            )
