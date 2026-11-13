import pandas as pd
from ipycanvas import Canvas
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="Click to place points", fillable=True)

points = reactive.value([])

with ui.layout_columns(col_widths=(7, 5)):
    with ui.card(full_screen=True):
        ui.p("Click anywhere on the canvas to drop a point.")

        @render_ipycanvas
        def canvas():
            c = Canvas(width=400, height=280)
            c.fill_style = "#f4f1ea"
            c.fill_rect(0, 0, 400, 280)

            def on_click(x, y):
                points.set(points() + [(x, y)])

            c.on_mouse_down(on_click)
            return c

    with ui.card():
        ui.card_header("Points (click order)")

        @render.data_frame
        def table():
            return pd.DataFrame(points(), columns=["x", "y"])


# Canvas content is stateless (draw commands, not widget state), so the
# simplest way to keep it in sync with `points` is to redraw everything each
# time it changes: clear, then replay.
@reactive.effect
def _draw_points():
    c = canvas.widget
    if c is None:
        return
    c.clear()
    c.fill_style = "#f4f1ea"
    c.fill_rect(0, 0, 400, 280)
    c.fill_style = "#c0392b"
    for x, y in points():
        c.fill_circle(x, y, 6)
