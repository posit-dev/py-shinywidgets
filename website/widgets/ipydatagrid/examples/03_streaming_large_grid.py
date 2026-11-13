import numpy as np
import pandas as pd
from ipydatagrid import StreamingDataGrid
from shiny.express import ui
from shinywidgets import render_ipydatagrid

rng = np.random.default_rng(0)
n = 200_000
big = pd.DataFrame(
    {
        "id": np.arange(n),
        "region": rng.choice(["North", "South", "East", "West"], n),
        "value": rng.normal(100, 20, n).round(2),
        "flag": rng.choice([True, False], n),
    }
)

ui.page_opts(fillable=True)

with ui.card(full_screen=True):
    ui.card_header(f"{n:,} rows, only the visible window crosses the wire")

    @render_ipydatagrid
    def grid():
        # StreamingDataGrid never sends the whole frame to the browser: it
        # keeps the data server-side and answers for the rows currently on
        # screen, plus server-side sort/filter. Pass a copy: it mutates the
        # frame it's given (adds a row-id column).
        return StreamingDataGrid(big.copy())
