import numpy as np
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_widget

from sparkline_widget import Sparkline

ui.page_opts(title="anywidget: custom messages both ways", fillable=True)
ui.input_action_button("flash", "Flash the line (Python -> JS message)")
ui.markdown("Double-click the line to send a message the other way (JS -> Python).")

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card():

        @render_widget
        def spark():
            rng = np.random.default_rng(2)
            return Sparkline(values=list(rng.normal(size=40).cumsum()))

        # Python -> JS, a custom message: `widget.send(...)` arrives in JS as
        # a "msg:custom" event (see sparkline_widget.py). A widget gets a
        # placeholder comm until the first post-render flush opens the real
        # one; a send made before then -- even from inside the render
        # function itself -- queues on that placeholder and is delivered, in
        # order, once the real comm opens, so it's never lost (see "Reacting
        # to user interaction" in the guide). The button click here is just
        # this toy app's trigger for "flash on demand," not a workaround.
        @reactive.effect
        @reactive.event(input.flash)
        def _flash():
            spark.widget.send({"type": "flash"})

    with ui.card():
        ui.card_header("Messages received from the widget")

        reset_count = reactive.value(0)

        @reactive.effect
        def _wire_on_msg():
            def _on_msg(widget, content, buffers):
                if content.get("type") == "reset-requested":
                    reset_count.set(reset_count() + 1)

            spark.widget.on_msg(_on_msg)

        @render.code
        def resets_out():
            idx = spark.read("clicked_index")
            return (
                f"clicks so far (via trait): {idx}\n"
                f"double-click messages received: {reset_count()}"
            )
