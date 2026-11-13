# Live trading desk (showcase)
#
# One streaming Perspective table feeds a blotter grid and a treemap at once;
# value boxes recompute server-side from exactly the blotter's current filter,
# a radio group swaps three viewer presets with hold_sync(), and a dark-mode
# switch updates both viewers' themes in place.
#
# Bucket: showcase (~155 lines)
# Run: uv run shiny run docs/widget-guides/perspective/gallery/showcase_trading_desk.py
# Data: synthesized in-process (random-walk trades)
#
# NOTE: `#`-comment header, not a module docstring -- see template_live_feed.py.

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from perspective import Server
from perspective.widget import PerspectiveWidget
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_perspective

SECTORS = {
    "Tech": ["AAPL", "MSFT", "NVDA", "GOOG"],
    "Finance": ["JPM", "GS", "BAC"],
    "Energy": ["XOM", "CVX"],
    "Health": ["JNJ", "PFE", "UNH"],
}
SECTOR_OF = {s: sec for sec, syms in SECTORS.items() for s in syms}
SYMS = list(SECTOR_OF)
rng = np.random.default_rng()
prices = dict(zip(SYMS, rng.uniform(40, 400, len(SYMS))))


def make_trades(n: int) -> pd.DataFrame:
    for s in SYMS:  # random-walk each symbol's price
        prices[s] *= 1 + rng.normal(0, 0.002)
    sym = rng.choice(SYMS, n)
    qty = rng.integers(1, 50, n) * 10
    px = np.array([prices[s] for s in sym]) * (1 + rng.normal(0, 0.0005, n))
    now = datetime.now()
    return pd.DataFrame(
        {
            "time": [
                now - timedelta(milliseconds=int(ms)) for ms in rng.integers(0, 500, n)
            ],
            "sector": [SECTOR_OF[s] for s in sym],
            "sym": sym,
            "side": rng.choice(["Buy", "Sell"], n),
            "qty": qty,
            "px": px.round(2),
            "notional": (px * qty).round(0),
            "pnl": (rng.normal(0, 1, n) * qty).round(2),
        }
    )


# Express re-runs this script once per session, so each session gets its own
# private table. `limit` keeps it a rolling window.
table = Server().new_local_client().table(make_trades(400), limit=3000)

TIME_FMT = {"date_format": {"dateStyle": "disabled", "timeStyle": "medium"}}
PRESETS: Dict[str, Dict[str, Any]] = {
    "Blotter": dict(
        plugin="Datagrid",
        group_by=[],
        split_by=[],
        sort=[["time", "desc"]],
        columns=["time", "sym", "side", "qty", "px", "notional", "pnl"],
        columns_config={
            "time": TIME_FMT,
            "notional": {"fg_mode": "bar", "fg_gradient": 150_000},
            "pnl": {"bg_mode": "gradient", "bg_gradient": 1_000},
        },
    ),
    "Pivot": dict(
        plugin="Datagrid",
        group_by=["sector", "sym"],
        split_by=["side"],
        sort=[],
        columns=["notional", "pnl"],
        # Python trait sets replace columns_config outright, but restoring it
        # from the browser's settings panel merges per column -- reset bars
        # explicitly instead of relying on {} to clear them.
        columns_config={
            "notional": {"fg_mode": "color"},
            "pnl": {"bg_mode": "gradient", "bg_gradient": 5_000},
        },
    ),
    "Heatmap": dict(
        plugin="Heatmap",
        group_by=["sym"],
        split_by=["side"],
        sort=[],
        columns=["pnl"],
        columns_config={},
    ),
}

ui.page_opts(title="Live trading desk", fillable=True)
ui.tags.style("#config { font-size: 0.8rem; white-space: pre-wrap; }")

with ui.sidebar(width=320):
    ui.input_switch("live", "Stream trades", True)
    ui.input_slider("rate", "Trades per tick (2 ticks/s)", 5, 200, 40)
    ui.input_radio_buttons("preset", "Left viewer layout", list(PRESETS), inline=True)
    ui.input_dark_mode(id="mode")
    ui.markdown(
        "Open a viewer's settings (`«`) to pivot, filter, or switch charts. "
        "Its filter syncs back to Python and drives the boxes above the "
        "viewers:"
    )

    @render.code
    def config():
        cfg = grid.view_config()
        keys = ["plugin", "group_by", "split_by", "filter"]
        body = "".join(f"  {k}={cfg[k]!r},\n" for k in keys)
        return f"PerspectiveWidget(\n  table,\n{body})"


tick = reactive.value(0)


@reactive.calc
def in_view() -> Dict[str, List[float]]:
    """The blotter's currently-filtered rows, computed in Python."""
    tick()
    view = table.view(filter=grid.filter(), columns=["notional", "pnl"])
    cols = view.to_columns()
    view.delete()  # views created from Python must be deleted, or they leak
    return cols


with ui.layout_columns(fill=False):
    with ui.value_box(theme="primary"):
        "Trades matching your filter"

        @render.text
        def n_trades():
            return f"{len(in_view()['pnl']):,} / {table.size():,}"

    with ui.value_box(theme="bg-gradient-indigo-purple"):
        "Notional"

        @render.text
        def notional():
            return f"${sum(in_view()['notional']) / 1e6:,.2f}M"

    with ui.value_box(theme="bg-gradient-teal-cyan"):
        "P&L"

        @render.text
        def pnl():
            return f"{sum(in_view()['pnl']):+,.0f}"


with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=True):

        @render_perspective
        def grid():
            return PerspectiveWidget(
                table, title="Trades", settings=False, **PRESETS["Blotter"]
            )

    with ui.card(full_screen=True):

        @render_perspective
        def chart():
            return PerspectiveWidget(
                table,
                plugin="Treemap",
                title="Notional by sector, colored by P&L",
                group_by=["sector", "sym"],
                columns=["notional", "pnl"],
                settings=False,
            )


@reactive.effect
def _stream():
    if input.live():
        reactive.invalidate_later(0.5)
        table.update(
            make_trades(input.rate())
        )  # both viewers repaint, nothing re-renders
        with reactive.isolate():
            tick.set(tick.get() + 1)


@reactive.effect
@reactive.event(input.preset)
def _apply_preset():
    with grid.widget.hold_sync():  # send the whole preset as one message
        for k, v in PRESETS[input.preset()].items():
            setattr(grid.widget, k, v)


@reactive.effect
def _theme():
    theme = "Pro Dark" if input.mode() == "dark" else "Pro Light"
    grid.widget.theme = chart.widget.theme = theme
