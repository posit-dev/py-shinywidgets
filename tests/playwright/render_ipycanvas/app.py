from __future__ import annotations

import numpy as np
from ipycanvas import Canvas
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipycanvas

CANVAS_W = 300
CANVAS_H = 200

app_ui = ui.page_fillable(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_action_button("draw_image", "Draw image"),
    ui.output_text("render_count"),
    ui.output_text("frame"),
    ui.output_text("mouse_pos"),
    # A fixed-height fillable container, to measure fill behavior against
    ui.card(output_widget("canvas"), style="height: 500px;"),
    # An output with an explicit height (which must be respected)
    output_widget("canvas_fixed", height="150px"),
)


def server(input, output, session):
    counter = reactive.value(0)
    frame_count = reactive.value(0)
    mouse = reactive.value("")

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render.text
    def mouse_pos():
        return mouse()

    @render.text
    def frame():
        return str(frame_count())

    def make_canvas() -> Canvas:
        c = Canvas(width=CANVAS_W, height=CANVAS_H)
        c.fill_style = "steelblue"
        c.fill_rect(10, 10, 100, 80)

        # A moderate-size image, to exercise binary (base64) transport
        img = np.zeros((60, 80, 4), dtype=np.uint8)
        img[..., 0] = 200  # red
        img[..., 3] = 255  # opaque
        c.put_image_data(img, 150, 10)

        c.on_mouse_down(lambda x, y: mouse.set(f"{round(x)},{round(y)}"))
        return c

    @render_ipycanvas
    def canvas():
        return make_canvas()

    @render_ipycanvas
    def canvas_fixed():
        return make_canvas()

    # Drive animation frames from Python, off the reactive cycle
    ticker = {"i": 0}

    @reactive.effect
    def _animate():
        reactive.invalidate_later(0.05)
        c = canvas.widget
        if c is None:
            return
        ticker["i"] += 1
        i = ticker["i"]
        x = (i * 5) % (CANVAS_W - 20)
        if x < 5:
            c.clear_rect(0, CANVAS_H - 40, CANVAS_W, 40)
        c.fill_style = "#e74c3c" if i % 2 else "#2ecc71"
        c.fill_rect(x, CANVAS_H - 40, 20, 20)
        frame_count.set(i)

    # Send a larger image on demand, so the test can time binary transport
    @reactive.effect
    @reactive.event(input.draw_image)
    def _():
        c = canvas.widget
        if c is None:
            return
        rng = np.random.default_rng(42)
        img = rng.integers(0, 255, size=(CANVAS_H, CANVAS_W, 4), dtype=np.uint8)
        img[..., 3] = 255
        c.put_image_data(img, 0, 0)


app = App(app_ui, server)
