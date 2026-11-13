from __future__ import annotations

import pandas as pd
from drawdata import ScatterWidget
from shiny.express import render, ui
from shinywidgets import render_drawdata

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=(7, 5)):
    with ui.card(full_screen=True):
        ui.card_header("Draw up to 4 classes")

        @render_drawdata
        def canvas():
            return ScatterWidget(width=800, height=400, n_classes=4)

    with ui.card(full_screen=True):
        ui.card_header("Rows, live")

        @render.data_frame
        def table():
            # canvas.widget.data_as_pandas is the same frame, but it's a plain
            # (non-reactive) property read -- it would compute once and never
            # update. Build the frame from .read("data") instead.
            data = canvas.read("data")
            return render.DataGrid(pd.DataFrame(data), height="100%")
