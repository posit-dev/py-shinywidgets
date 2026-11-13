import numpy as np
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_widget

from sparkline_widget import Sparkline

ui.page_opts(title="anywidget: trait sync both ways", fillable=True)
ui.input_action_button("new_data", "New random walk")

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card():
        ui.card_header("Click the line -- JS reports the nearest point to Python")

        @render_widget
        def spark():
            rng = np.random.default_rng(1)
            return Sparkline(values=list(rng.normal(size=40).cumsum()))

        # Python -> JS: a NEW `values` list is pushed into the SAME widget
        # instance (spark.widget), so the canvas redraws in place -- no
        # re-render, no new comm, no re-sent JS bundle.
        @reactive.effect
        @reactive.event(input.new_data)
        def _new_walk():
            rng = np.random.default_rng()
            spark.widget.values = list(rng.normal(size=40).cumsum())

    with ui.card():
        ui.card_header('spark.read("clicked_index")')

        @render.code
        def clicked_out():
            idx = spark.read("clicked_index")
            return "click the sparkline" if idx is None else f"clicked index: {idx}"
