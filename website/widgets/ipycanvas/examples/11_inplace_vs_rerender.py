from ipycanvas import Canvas
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="In-place updates vs re-render", fillable=True)

rerender_trigger = reactive.value(0)
drawing = {"last": None}

with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):
        ui.p("Draw a few strokes, change the square's color, then force a re-render.")

        @render_ipycanvas
        def canvas():
            rerender_trigger()  # reading this makes re-render wipe everything below
            c = Canvas(width=360, height=240)
            c.fill_style = "#f4f1ea"
            c.fill_rect(0, 0, 360, 240)
            c.fill_style = "steelblue"
            c.fill_rect(20, 20, 80, 80)

            def on_down(x, y):
                drawing["last"] = (x, y)

            def on_move(x, y):
                if drawing["last"] is None:
                    return
                c.stroke_style = "#333"
                c.line_width = 2
                c.stroke_line(*drawing["last"], x, y)
                drawing["last"] = (x, y)

            def on_up(x, y):
                drawing["last"] = None

            c.on_mouse_down(on_down)
            c.on_mouse_move(on_move)
            c.on_mouse_up(on_up)
            c.on_mouse_out(on_up)
            return c

    with ui.card():
        ui.card_header("Controls")
        ui.input_select(
            "color", "Square color", ["steelblue", "firebrick", "seagreen"]
        )
        ui.input_action_button("rerender", "Force full re-render (loses strokes)")


# Runs on every color change, but never re-runs the render function above:
# drawing directly on `.widget` updates the browser canvas in place, so the
# hand-drawn strokes are untouched. Re-rendering (the other effect below)
# tears the widget down and rebuilds it from scratch instead -- simpler, but
# it loses anything drawn outside the render function.
@reactive.effect
def _update_square():
    c = canvas.widget
    if c is not None:
        c.fill_style = input.color()
        c.fill_rect(20, 20, 80, 80)


@reactive.effect
@reactive.event(input.rerender)
def _force_rerender():
    rerender_trigger.set(rerender_trigger() + 1)
