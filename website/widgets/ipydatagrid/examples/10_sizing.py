import pandas as pd
from ipydatagrid import DataGrid
from shiny.express import ui
from shinywidgets import render_ipydatagrid

df = pd.DataFrame({"name": ["Ann", "Bo", "Cy"], "score": [91, 72, 88]})

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=True):
        ui.card_header("Default column widths leave a void in a wide card")

        @render_ipydatagrid
        def grid_default():
            return DataGrid(df)

    with ui.card(full_screen=True):
        ui.card_header("column_widths= stretches columns to fill")

        @render_ipydatagrid
        def grid_sized():
            return DataGrid(df, column_widths={"name": 300, "score": 300})
