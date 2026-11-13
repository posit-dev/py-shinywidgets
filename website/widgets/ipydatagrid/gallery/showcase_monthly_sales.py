# Monthly sales spreadsheet
#
# A heatmap of monthly sales, bar-rendered totals, and conditionally colored
# year-over-year change -- editable, with the total/YoY columns recomputing in
# place after an edit, a drag-to-select status bar, and a side chart that
# redraws to show the monthly profile of whatever rows are selected.
#
# Bucket: showcase (~170 lines)
# Run: uv run --no-sync shiny run docs/widget-guides/ipydatagrid/gallery/showcase_monthly_sales.py
# Data: synthesized in-line (numpy); flat region/product columns (no MultiIndex
# -- ipydatagrid's merged row-header groups go stale after a sort, so this
# avoids that upstream bug entirely).
#
# NOTE: this header is a comment, not a module docstring -- Shiny Express
# auto-displays a leading string-literal expression as page content, so a
# real docstring here would render as visible text above the app.

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from bqscales import ColorScale, LinearScale
from ipydatagrid import BarRenderer, DataGrid, TextRenderer, VegaExpr
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import render_ipydatagrid, render_plotly

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
REGIONS = ["North", "South", "East", "West"]
PRODUCTS = ["Anchor", "Beacon", "Comet"]

rng = np.random.default_rng(42)
rows = [(r, p) for r in REGIONS for p in PRODUCTS]
df = pd.DataFrame(
    {"region": [r for r, _ in rows], "product": [p for _, p in rows]}
    | {m: rng.integers(30, 150, len(rows)) for m in MONTHS}
)
df["total"] = df[MONTHS].sum(axis=1)
df["yoy"] = rng.uniform(-0.25, 0.35, len(rows)).round(3)

ui.page_opts(fillable=True, title="Monthly sales")

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header(
            "Drag to select a block; double-click a month to edit "
            "(Total and YoY recompute)"
        )

        @render_ipydatagrid
        def grid():
            heatmap = TextRenderer(
                background_color=ColorScale(min=30, max=150, scheme="Blues"),
                format=",",
            )
            bars = BarRenderer(
                bar_value=LinearScale(min=0, max=int(df["total"].max() * 1.2)),
                bar_color="#4C78A8",
                format=",",
            )
            yoy_color = TextRenderer(
                text_color=VegaExpr("cell.value >= 0 ? '#1a7f37' : '#cf222e'"),
                format="+.1%",
            )
            return DataGrid(
                df,
                renderers={
                    **{m: heatmap for m in MONTHS},
                    "total": bars,
                    "yoy": yoy_color,
                },
                selection_mode="cell",
                editable=True,
                column_widths={"region": 90, "product": 90},
            )

    with ui.card():
        ui.card_header("Status bar")

        @render.ui
        def status():
            sels = grid.selected()
            if not sels:
                return "Select a block of cells."
            vis = grid.visible_data()
            # A selection can span the text region/product columns too, so
            # slice first, then keep only the numeric columns of that slice.
            pieces = [
                vis.iloc[s["r1"] : s["r2"] + 1, s["c1"] : s["c2"] + 1]
                .select_dtypes("number")
                .to_numpy()
                .ravel()
                for s in sels
            ]
            block = np.concatenate(pieces) if pieces else np.array([])
            if block.size == 0:
                return "Selection has no numeric cells."
            return ui.TagList(
                ui.p(f"Count {block.size} · Sum {block.sum():.0f}"),
                ui.p(
                    f"Average {block.mean():.1f} · Min {block.min():.0f} · "
                    f"Max {block.max():.0f}"
                ),
            )

        ui.card_header("Monthly profile (selected rows vs. all rows)")

        @render_plotly
        def profile():
            # A FigureWidget built once, then updated in place below -- not
            # rebuilt on every selection change. `selected()` debounces by
            # default, so this only fires once a drag settles, but rebuilding
            # a whole plotly figure from scratch is still slower and flashes
            # visibly compared to updating its trace data in place.
            overall = df[MONTHS].mean()
            fig = go.FigureWidget(
                go.Scatter(x=MONTHS, y=overall, name="All rows", line_color="#999")
            )
            fig.add_scatter(
                x=MONTHS, y=overall, name="Selected", line_color="#4C78A8",
                visible=False,
            )
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=220)
            return fig


@reactive.effect
def _update_profile():
    sels = grid.selected()
    grid.edited_cell()  # also redraw "All rows" after an edit changes a month
    with reactive.isolate():
        profile.widget.data[0].y = grid.widget.data[MONTHS].mean().tolist()
        if not sels:
            profile.widget.data[1].visible = False
            return
        vis = grid.visible_data()
        rows_idx = sorted({r for s in sels for r in range(s["r1"], s["r2"] + 1)})
        selected = vis.iloc[rows_idx][MONTHS].mean()
        profile.widget.data[1].y = selected.tolist()
        profile.widget.data[1].visible = True


@reactive.effect
def _recompute_row():
    edit = grid.edited_cell()
    req(edit)
    if edit["column"] not in MONTHS:
        return  # ignore the write-echo from our own total/yoy writes below
    with reactive.isolate():
        row = edit["row"]
        data = grid.widget.data
        new_total = int(data.loc[row, MONTHS].sum())
        old_total = data.loc[row, "total"]
        grid.widget.set_cell_value_by_index("total", row, new_total)
        if old_total:
            yoy = round((new_total - old_total) / old_total, 3)
            grid.widget.set_cell_value_by_index("yoy", row, yoy)
