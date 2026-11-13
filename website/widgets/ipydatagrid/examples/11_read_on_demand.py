import pandas as pd
from ipydatagrid import DataGrid
from shiny.express import render, ui
from shinywidgets import render_ipydatagrid

df = pd.DataFrame(
    {
        "sku": [f"SKU-{100 + i}" for i in range(12)],
        "name": [f"Product {i}" for i in range(12)],
        "price": [round(9.99 + i * 3.5, 2) for i in range(12)],
    }
)

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Select rows, then export -- no need to display them first")

        @render_ipydatagrid
        def grid():
            return DataGrid(df, selection_mode="row")

    with ui.card():
        ui.card_header("Export")
        ui.p("Nothing on this page reads selected() until you click Download.")

        @render.download_button(filename="selected_rows.csv", label="Download selected rows")
        def export():
            # Read on demand: no warm-up, no earlier display of this value --
            # selected() and visible_data() already hold the latest
            # selection the moment the handler runs.
            sels = grid.selected()
            rows = sorted({r for s in sels for r in range(s["r1"], s["r2"] + 1)})
            out = grid.visible_data().iloc[rows]
            yield out.to_csv(index=False).encode()
