import time

from ipycanvas import Canvas
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="Rate limiting mouse events", fillable=True)

# ipycanvas events have no built-in rate policy (that's an accessor feature;
# a raw on_mouse_move callback fires on every browser mousemove, easily
# 60+ times/sec). Throttle yourself: gate expensive work behind a timestamp,
# but keep a cheap counter ungated if you want every event to register.
event_count = reactive.value(0)
sampled_count = reactive.value(0)
_last_sample = {"t": 0.0}
THROTTLE_S = 0.1

with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):

        @render_ipycanvas
        def canvas():
            c = Canvas(width=420, height=240)

            def on_move(x, y):
                event_count.set(event_count() + 1)  # cheap, update every time
                now = time.monotonic()
                if now - _last_sample["t"] < THROTTLE_S:
                    return  # too soon since the last sample -- drop it
                _last_sample["t"] = now
                sampled_count.set(sampled_count() + 1)  # drives expensive work

            c.on_mouse_move(on_move)
            return c

    with ui.card():
        ui.card_header("Event volume")

        @render.text
        def counts():
            return (
                f"Raw mouse_move events: {event_count()}\n"
                f"Throttled samples (every {THROTTLE_S * 1000:.0f}ms): {sampled_count()}"
            )
