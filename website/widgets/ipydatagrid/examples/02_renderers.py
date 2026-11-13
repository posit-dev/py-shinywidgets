import numpy as np
import pandas as pd
from bqscales import ColorScale, LinearScale
from ipydatagrid import BarRenderer, DataGrid, TextRenderer, VegaExpr
from shiny.express import ui
from shinywidgets import render_ipydatagrid

rng = np.random.default_rng(3)
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
sales = pd.DataFrame(
    {"product": [f"Widget {c}" for c in "ABCDEFGH"]}
    | {m: rng.integers(20, 200, 8) for m in months}
)
sales["total"] = sales[months].sum(axis=1)
sales["yoy"] = rng.uniform(-0.3, 0.4, 8).round(3)

ui.page_opts(fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Renderers: heatmap, bars, and conditional color")

    @render_ipydatagrid
    def grid():
        # Renderers and scales are widgets, so build them here (inside the
        # render function), not at module import time.
        heatmap = TextRenderer(
            background_color=ColorScale(min=20, max=200, scheme="Blues"),
            format=",",
        )
        bars = BarRenderer(
            # LinearScale's min/max are plain Python floats, not numpy scalars
            bar_value=LinearScale(min=0, max=float(sales["total"].max())),
            bar_color="#4C78A8",
            format=",",
        )
        yoy_color = TextRenderer(
            text_color=VegaExpr("cell.value >= 0 ? '#1a7f37' : '#cf222e'"),
            format="+.1%",
        )
        return DataGrid(
            sales,
            renderers={**{m: heatmap for m in months}, "total": bars, "yoy": yoy_color},
            selection_mode="none",
            column_widths={"product": 90},
        )
