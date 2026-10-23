import numpy as np
from ipycanvas import Canvas, RoughCanvas
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_ipycanvas

DRAW_W, DRAW_H = 640, 360
ANIM_W, ANIM_H = 640, 200

COLORS = {"steelblue": "#4682b4", "firebrick": "#b22222", "seagreen": "#2e8b57"}

app_ui = ui.page_fillable(
    ui.h2("ipycanvas in Shiny"),
    ui.layout_columns(
        ui.card(
            ui.card_header("Draw with your mouse"),
            ui.input_select(
                "color", "Color", choices=["steelblue", "firebrick", "seagreen"]
            ),
            output_widget("draw"),
        ),
        ui.card(
            ui.card_header("Animation driven by Python"),
            ui.input_action_button("toggle", "Play/pause"),
            output_widget("anim"),
        ),
        col_widths=(7, 5),
    ),
)


def server(input, output, session):
    # ------------------------------------------------------------------
    # Interactive drawing: browser mouse events fire Python callbacks
    # ------------------------------------------------------------------
    drawing = {"last": None}

    @render_ipycanvas
    def draw():
        c = Canvas(width=DRAW_W, height=DRAW_H)

        # put_image_data() sends a binary buffer (a NumPy array, PNG-encoded
        # by ipycanvas) over the websocket
        img = np.zeros((60, 60, 4), dtype=np.uint8)
        img[..., 1] = 180
        img[..., 3] = 80
        c.put_image_data(img, DRAW_W - 70, DRAW_H - 70)

        def mouse_down(x, y):
            drawing["last"] = (x, y)

        def mouse_move(x, y):
            if drawing["last"] is None:
                return
            c.stroke_style = COLORS[input.color()]
            c.line_width = 3
            c.stroke_line(*drawing["last"], x, y)
            drawing["last"] = (x, y)

        def mouse_up(x, y):
            drawing["last"] = None

        c.on_mouse_down(mouse_down)
        c.on_mouse_move(mouse_move)
        c.on_mouse_up(mouse_up)
        c.on_mouse_out(mouse_up)
        return c

    # ------------------------------------------------------------------
    # Animation: frames are produced by Python, off the reactive cycle
    # ------------------------------------------------------------------
    running = reactive.value(False)
    ball = {"x": 50.0, "y": 50.0, "vx": 3.0, "vy": 2.2}

    @render_ipycanvas
    def anim():
        c = RoughCanvas(width=ANIM_W, height=ANIM_H)
        c.rough_fill_style = "solid"
        return c

    @reactive.effect
    @reactive.event(input.toggle)
    def _():
        running.set(not running())

    @reactive.effect
    def _animate():
        reactive.invalidate_later(1 / 60)
        if not running():
            return
        c = anim.widget
        if c is None:
            return
        b = ball
        b["x"] += b["vx"]
        b["y"] += b["vy"]
        if not 20 < b["x"] < ANIM_W - 20:
            b["vx"] = -b["vx"]
        if not 20 < b["y"] < ANIM_H - 20:
            b["vy"] = -b["vy"]
        c.clear()
        c.fill_style = "#e67e22"
        c.fill_circle(b["x"], b["y"], 15)


app = App(app_ui, server)
