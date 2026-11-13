import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ipydatagrid import DataGrid
from shiny.express import ui
from shinywidgets import render_ipydatagrid, render_plotly

rng = np.random.default_rng(4)
stores = pd.DataFrame(
    {
        "store": [f"Store {i}" for i in range(15)],
        "region": rng.choice(["North", "South"], 15),
        "revenue": rng.integers(50, 500, 15),
    }
)

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Sort or filter from a column header's menu icon")

        @render_ipydatagrid
        def grid():
            return DataGrid(stores, selection_mode="none")

    with ui.card():
        ui.card_header("Chart of only what's currently visible")

        @render_plotly
        def chart():
            vis = grid.visible_data()
            return go.Figure(go.Bar(x=vis["store"], y=vis["revenue"]))
