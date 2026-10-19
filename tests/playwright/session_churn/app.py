import gc
import json

import ipywidgets as W
from ipywidgets import Widget
from ipywidgets.widgets.widget import _instances
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget, session_lifetime
from shinywidgets._shinywidgets import (
    COMM_MANAGERS,
    KEPT_WIDGETS,
    RENDER_OWNED_WIDGETS,
    SESSION_WIDGET_ID_MAP,
)

# 10 sessions opened and closed, then one surviving session's state should
# be intact and the global per-session maps should hold only that session's
# entries. `probe` exposes server-side state so the test can read it without
# any client-side instrumentation.
app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_select("key", "Cached key", ["A", "B"]),
    ui.output_text("probe"),
    output_widget("r"),
    output_widget("s"),
    output_widget("c"),
)


def server(input, output, session):
    held = W.Button(description="session-owned")
    cache: dict[str, W.HTML] = {}

    @render_widget
    def r():
        return W.VBox([W.Button(description=f"r {input.rerender()}"), W.IntSlider()])

    @render_widget
    def s():
        return held

    @render_widget
    def c():
        key = input.key()
        if key not in cache:
            with session_lifetime():
                cache[key] = W.HTML(value=f"cached {key}")
        return cache[key]

    @render.text
    def probe():
        reactive.invalidate_later(0.25)
        gc.collect()
        return json.dumps(
            {
                "gc_widgets": sum(isinstance(o, Widget) for o in gc.get_objects()),
                "server_widgets": len(_instances),
                "comm_managers": len(COMM_MANAGERS),
                "session_widget_id_map": len(SESSION_WIDGET_ID_MAP),
                "render_owned_widgets": len(RENDER_OWNED_WIDGETS),
                "kept_widgets": len(KEPT_WIDGETS),
            }
        )


app = App(app_ui, server)
