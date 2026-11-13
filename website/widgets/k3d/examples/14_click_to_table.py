# Pairs with: itables, reactable (swap render.data_frame for either).
from __future__ import annotations

import k3d
import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_k3d

rng = np.random.default_rng(1)
xyz = (rng.normal(size=(20, 3))).astype(np.float32)
df = pd.DataFrame(xyz.astype(np.float64), columns=["x", "y", "z"]).round(2)

clicked_index = reactive.value(None)

ui.page_opts(title="Click a point, select its row", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("plot.mode = 'callback'")

        @render_k3d
        def scene():
            plot = k3d.plot(mode="callback")
            plot += k3d.points(
                xyz,
                point_size=0.12,
                color=0x4C78A8,
                click_callback=lambda info: clicked_index.set(info["index"]),
            )
            return plot

    with ui.card(full_screen=True):
        ui.card_header("Matching row, selected")

        @render.data_frame
        def table():
            return render.DataGrid(df, selection_mode="row")


# A DataGrid's row selection is driven from the server with
# update_cell_selection() (async, so this effect must be too).
@reactive.effect
async def _select():
    idx = clicked_index()
    if idx is not None:
        await table.update_cell_selection({"type": "row", "rows": (idx,)})
