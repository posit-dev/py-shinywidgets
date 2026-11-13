from ipycanvas import Canvas
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="Mouse events as reactive input", fillable=True)

# The recipe: an ipycanvas callback (on_mouse_down/move/up) is a plain Python
# function, called outside any reactive context. Inside it, call .set() on a
# reactive.value -- that's the one hop from "browser event" to "Shiny input".
last_point = reactive.value(None)
stroke_count = reactive.value(0)
drawing = {"active": False}

with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):

        @render_ipycanvas
        def canvas():
            c = Canvas(width=420, height=260)
            c.fill_style = "#f4f1ea"
            c.fill_rect(0, 0, 420, 260)

            def on_down(x, y):
                drawing["active"] = True
                stroke_count.set(stroke_count() + 1)
                last_point.set((x, y))

            def on_move(x, y):
                if not drawing["active"]:
                    return
                c.stroke_style = "#2c7fb8"
                c.line_width = 3
                c.stroke_line(*last_point(), x, y)
                last_point.set((x, y))

            def on_up(x, y):
                drawing["active"] = False

            c.on_mouse_down(on_down)
            c.on_mouse_move(on_move)
            c.on_mouse_up(on_up)
            c.on_mouse_out(on_up)
            return c

    with ui.card():
        ui.card_header("What Python saw")

        @render.text
        def info():
            pt = last_point()
            pt_str = f"{pt[0]:.0f}, {pt[1]:.0f}" if pt else "none yet"
            return f"Strokes started: {stroke_count()}\nLast point: {pt_str}"
