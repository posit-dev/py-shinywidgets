from ipycanvas import Canvas
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="Keyboard events", fillable=True)

# A canvas is focusable: click it once, then on_key_down fires like any other
# keydown handler -- key, shift_key, ctrl_key, meta_key.
pos = {"x": 100, "y": 90}
last_key = reactive.value(None)
STEP = 15
MOVES = {
    "ArrowUp": (0, -STEP),
    "ArrowDown": (0, STEP),
    "ArrowLeft": (-STEP, 0),
    "ArrowRight": (STEP, 0),
}

with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):
        ui.p("Click the canvas, then use the arrow keys.")

        @render_ipycanvas
        def canvas():
            c = Canvas(width=320, height=240)

            def redraw():
                c.clear()
                c.fill_style = "#8e44ad"
                c.fill_rect(pos["x"], pos["y"], 30, 30)

            def on_key(key, shift_key, ctrl_key, meta_key):
                last_key.set(key)
                dx, dy = MOVES.get(key, (0, 0))
                pos["x"] = min(max(pos["x"] + dx, 0), 290)
                pos["y"] = min(max(pos["y"] + dy, 0), 210)
                redraw()

            c.on_key_down(on_key)
            redraw()
            return c

    with ui.card():
        ui.card_header("Last key")

        @render.text
        def key_text():
            return last_key() or "(click the canvas first)"
