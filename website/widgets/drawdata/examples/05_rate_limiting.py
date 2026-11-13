from __future__ import annotations

from drawdata import BarWidget
from shiny.express import render, ui
from shinywidgets import render_drawdata

ui.page_opts(fillable=True)

ui.markdown(
    "Drag across the bars below. `BarWidget` writes its `data` trait on "
    "*every* pointer move while dragging, not just on mouse-up -- so an "
    "unthrottled `.read(\"data\")` re-runs dozens of times per drag."
)

# Plain counters (not reactive.Value): each render function below just needs
# to remember how many times *it* has run, not notify anything else.
counts = {"unthrottled": 0, "throttled": 0}

with ui.layout_columns():
    with ui.card():
        ui.card_header("Unthrottled")

        @render_drawdata
        def unthrottled():
            return BarWidget(collection_names=["dist"])

        @render.code
        def n_unthrottled():
            unthrottled.read("data")
            counts["unthrottled"] += 1
            return f".read() ran {counts['unthrottled']} times"

    with ui.card():
        ui.card_header("Throttled: rate_policy='throttle', rate_delay=1")

        @render_drawdata(rate_policy="throttle", rate_delay=1)
        def throttled():
            return BarWidget(collection_names=["dist"])

        @render.code
        def n_throttled():
            throttled.read("data")
            counts["throttled"] += 1
            return f".read() ran {counts['throttled']} times"
