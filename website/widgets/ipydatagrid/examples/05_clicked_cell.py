import pandas as pd
from ipydatagrid import DataGrid
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_ipydatagrid

products = pd.DataFrame(
    {
        "sku": [f"SKU-{100 + i}" for i in range(12)],
        "name": [f"Product {i}" for i in range(12)],
        "category": (["Tools", "Garden", "Kitchen"] * 4),
        "price": [round(9.99 + i * 3.5, 2) for i in range(12)],
    }
)

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Click any cell, in any selection mode (even 'none')")

        @render_ipydatagrid
        def grid():
            # selection_mode="none" disables selected(), but clicked_cell()
            # still fires -- it isn't tied to selection_mode.
            return DataGrid(products, selection_mode="none")

    with ui.card():
        ui.card_header("Detail card")

        @render.ui
        def detail():
            click = grid.clicked_cell()
            req(click)
            # `row` is the visible position (after any sort); `primary_key_row`
            # is the underlying data row. Use get_visible_data() to look up
            # the full record the user actually clicked on.
            record = grid.widget.get_visible_data().iloc[click["row"]]
            return ui.TagList(
                ui.h5(record["name"]),
                ui.p(f"{record['sku']} · {record['category']} · ${record['price']}"),
                ui.p(f"Clicked column: {click['column']!r}, region: {click['region']!r}"),
            )
