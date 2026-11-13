import plotly.express as px
from ipydatagrid import DataGrid
from shiny.express import render, ui
from shinywidgets import render_ipydatagrid

tips = px.data.tips()  # 244 restaurant bills: total_bill, tip, sex, smoker, day, time, size

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header(
            "Click or drag to select rows; use a column header's "
            "menu icon to sort or filter"
        )

        @render_ipydatagrid
        def grid():
            return DataGrid(tips, selection_mode="row")

    with ui.card():
        ui.card_header("Selected rows")

        @render.data_frame
        def selected():
            rows = sorted(
                {r for s in grid.selected() for r in range(s["r1"], s["r2"] + 1)}
            )
            return grid.visible_data().iloc[rows].reset_index(drop=True)
