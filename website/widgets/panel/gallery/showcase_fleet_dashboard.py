# Title: Server fleet dashboard (table + indicators + chat)
# Bucket: showcase
# One-line: A Panel Tabulator, two live indicators, and a canned-reply chat
#   assistant, all wired together with Shiny reactivity and no Panel server.
# Run: uv run --no-sync shiny run docs/widget-guides/panel/gallery/showcase_fleet_dashboard.py
# Data: synthetic but plausible fleet metrics (generated below with numpy;
#   point is combining several Panel component families, not the data itself)
import numpy as np
import pandas as pd
import panel as pn
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_panel

pn.extension("tabulator")

rng = np.random.default_rng(42)
regions = ["us-east", "us-west", "eu-west", "ap-south"]
n = 24
fleet = pd.DataFrame(
    {
        "server": [f"srv-{i:03d}" for i in range(n)],
        "region": rng.choice(regions, n),
        "cpu_pct": np.clip(rng.normal(55, 20, n), 2, 99).round(1),
        "mem_pct": np.clip(rng.normal(60, 15, n), 5, 98).round(1),
    }
)
fleet["status"] = np.where(
    fleet["cpu_pct"] > 85, "critical", np.where(fleet["cpu_pct"] > 65, "warning", "ok")
)

ui.page_opts(title="Fleet dashboard", fillable=True)

with ui.layout_columns(col_widths=[6, 6], fill=False, height="220px"):
    with ui.card():
        ui.card_header("CPU")

        @render_panel
        def cpu_dial():
            return pn.indicators.Dial(
                name="Select a server", value=0, bounds=(0, 100),
                format="{value:.0f}%", width=180, height=180,
                colors=[(0.65, "#1a9850"), (0.85, "#fdae61"), (1, "#d7301f")],
            )

    with ui.card():
        ui.card_header("Memory")

        @render_panel
        def mem_number():
            return pn.indicators.Number(
                name="Select a server", value=0, format="{value:.0f}% mem",
                sizing_mode="stretch_width",
            )

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Fleet (click a server)")

        @render_panel
        def table():
            return pn.widgets.Tabulator(
                fleet, selectable=1, disabled=True, theme="bootstrap5",
                layout="fit_columns", sizing_mode="stretch_both",
                formatters={
                    "cpu_pct": {"type": "progress", "min": 0, "max": 100,
                                "color": ["#1a9850", "#fdae61", "#d7301f"]},
                    "mem_pct": {"type": "progress", "min": 0, "max": 100,
                                "color": ["#1a9850", "#fdae61", "#d7301f"]},
                },
            )

    with ui.card(full_screen=True):
        ui.card_header("Ask about the fleet")

        @render_panel
        def chat():
            return pn.chat.ChatInterface(
                callback=fleet_reply, show_rerun=False, show_undo=False,
                sizing_mode="stretch_both",
            )


def fleet_reply(contents: str, user: str, instance: pn.chat.ChatInterface) -> str:
    text = contents.lower()
    if "critical" in text:
        rows = fleet[fleet["status"] == "critical"]
        return f"{len(rows)} server(s) critical: {', '.join(rows['server']) or 'none'}"
    if "average cpu" in text or "avg cpu" in text:
        return f"Average CPU across the fleet: {fleet['cpu_pct'].mean():.1f}%"
    if "region" in text:
        counts = fleet["region"].value_counts()
        return "; ".join(f"{r}: {c}" for r, c in counts.items())
    return "Try asking about 'critical servers', 'average cpu', or 'region'."


@reactive.effect
def _():
    idx = table.param("selection")
    dial, number = cpu_dial.value, mem_number.value
    if not idx:
        dial.name, dial.value = "Select a server", 0
        number.name, number.value = "Select a server", 0
    else:
        row = table.value.value.iloc[idx[0]]
        dial.name, dial.value = row["server"], row["cpu_pct"]
        number.name, number.value = f"{row['server']} memory", row["mem_pct"]
