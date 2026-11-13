from ipycanvas import Canvas, hold_canvas
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="hold_canvas", fillable=True)

# ipycanvas's hold_canvas() batches draw commands by toggling a *module-level*
# manager shared by every kernel. shinywidgets gives each rendered canvas its
# own per-session manager (so one session's drawing can't leak into another's
# browser) -- so hold_canvas() ends up toggling a manager nobody's canvas is
# actually using. Drawing inside the block still works, command by command,
# just not batched into one network message. Safe to leave in shared
# Jupyter/Shiny code; just don't rely on it for Shiny's own perf.

with ui.card(full_screen=True):
    ui.input_action_button("draw", "Draw 8 bars (inside hold_canvas)", class_="mb-2")

    @render_ipycanvas
    def canvas():
        return Canvas(width=420, height=220)

    @reactive.effect
    @reactive.event(input.draw)
    def _():
        c = canvas.widget
        if c is None:
            return
        c.clear()
        with hold_canvas(c):
            for i in range(8):
                c.fill_style = f"hsl({i * 40}, 65%, 55%)"
                c.fill_rect(10 + i * 50, 20, 40, 20 + i * 20)
