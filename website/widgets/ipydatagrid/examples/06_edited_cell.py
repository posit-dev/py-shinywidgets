import pandas as pd
import plotly.graph_objects as go
from ipydatagrid import DataGrid
from shiny import reactive, req
from shiny.express import ui
from shinywidgets import render_ipydatagrid, render_plotly

months = ["Jan", "Feb", "Mar"]
df = pd.DataFrame(
    {
        "product": ["Widget A", "Widget B", "Widget C"],
        "Jan": [120, 90, 60],
        "Feb": [140, 95, 70],
        "Mar": [160, 100, 80],
    }
)
df["total"] = df[months].sum(axis=1)

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Double-click a month to edit; Total recomputes in place")

        @render_ipydatagrid
        def grid():
            return DataGrid(df, selection_mode="none", editable=True)

    with ui.card():
        ui.card_header("Totals (updates without re-rendering the chart)")

        @render_plotly
        def chart():
            return go.FigureWidget(
                go.Bar(x=df["product"], y=df["total"], marker_color="#4C78A8")
            )


@reactive.effect
def _recompute_total():
    edit = grid.edited_cell()
    req(edit)
    if edit["column"] not in months:
        return  # ignore the write-echo when we ourselves edit `total` below
    with reactive.isolate():
        row = edit["row"]
        total = int(grid.widget.data.loc[row, months].sum())
        grid.widget.set_cell_value_by_index("total", row, total)
        # In-place trait update: no re-render, so the chart keeps its zoom
        # and hover state, and the JS bundle isn't re-sent.
        chart.widget.data[0].y = grid.widget.data["total"].tolist()
