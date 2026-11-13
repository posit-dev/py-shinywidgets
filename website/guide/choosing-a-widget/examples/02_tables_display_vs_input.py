# The same data frame through three table outputs, to show what each adds
# over plain Shiny: render.data_frame (free, built in, virtualized), itables
# (global search, export, zero config), ipydatagrid (cell-block selection,
# editable cells). None of these needs the others -- pick by what the task
# needs, not by default.
# Run: uv run shiny run docs/widget-guides/articles/choosing-a-widget/examples/02_tables_display_vs_input.py
import plotly.express as px
from ipydatagrid import DataGrid
from itables.widget import ITable
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_ipydatagrid, render_itables

ui.page_opts(title="Tables: plain Shiny vs. itables vs. ipydatagrid", fillable=True)

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)
cols = ["country", "continent", "lifeExp", "gdpPercap", "pop"]

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("render.data_frame -- plain Shiny, no extra JS")

        @render.data_frame
        def grid_plain():
            return render.DataGrid(df[cols], selection_mode="row", filters=True)

        @render.code
        def sel_plain():
            idx = grid_plain.cell_selection()["rows"]
            return f"{len(idx)} row(s) selected (click a row)"

    with ui.card(full_screen=True):
        ui.card_header("itables -- global search + export, built in")

        @render_itables
        def table_itables():
            return ITable(df[cols], select=True, buttons=["csvHtml5"])

        @render.code
        def sel_itables():
            n = len(table_itables.selected_rows())
            return f"{n} row(s) selected (click to search/select)"

    with ui.card(full_screen=True):
        ui.card_header("ipydatagrid -- rectangular cell-block selection")

        @render_ipydatagrid
        def grid_datagrid():
            return DataGrid(df[cols], selection_mode="cell")

        @render.code
        def sel_datagrid():
            blocks = req(grid_datagrid.selected())
            r1, r2 = blocks[0]["r1"], blocks[0]["r2"]
            c1, c2 = blocks[0]["c1"], blocks[0]["c2"]
            return f"block: rows {r1}-{r2}, cols {c1}-{c2} (click, then shift-click)"
