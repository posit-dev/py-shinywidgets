from __future__ import annotations

from drawdata import BarWidget, ScatterWidget
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_drawdata

ui.page_opts(fillable=True)

# BarWidget ignores Python-side trait writes after it first renders (its
# frontend registers no `change:` handlers), so the only way to reset one is
# to re-render it. Bumping this counter -- read, but otherwise unused, inside
# the render function -- forces exactly that.
bar_generation = reactive.Value(0)

with ui.layout_columns():
    with ui.card():
        ui.card_header("ScatterWidget: cleared in place")

        @render_drawdata
        def canvas():
            return ScatterWidget(width=800, height=400, n_classes=2)

        ui.input_action_button("clear_canvas", "Clear")

    with ui.card():
        ui.card_header("BarWidget: reset by re-rendering")

        @render_drawdata
        def hist():
            bar_generation()
            return BarWidget(collection_names=["dist"])

        ui.input_action_button("reset_hist", "Reset")


@render.code
def counts():
    s = canvas.read("data")
    b = [d for d in hist.read("data") if d["value"] != 0]
    return f"scatter: {len(s)} points  |  bar: {len(b)} raised bins"


@reactive.effect
@reactive.event(input.clear_canvas)
def _clear_canvas():
    # ScatterWidget *does* have a change:data handler, so this both updates
    # the Python-side trait and clears the browser canvas immediately.
    canvas.widget.data = []


@reactive.effect
@reactive.event(input.reset_hist)
def _reset_hist():
    bar_generation.set(bar_generation() + 1)
