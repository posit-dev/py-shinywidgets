# camera() has no default rate policy (k3d already throttles camera updates to
# ~200ms upstream), so `rate_policy`/`rate_delay` have nothing to add there.
# They do matter for a plain .read() on a fast-changing trait, like "time"
# during autoplay (k3d ticks it at its own `fps`, default 25/s).
from __future__ import annotations

import k3d
import numpy as np
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_k3d


def make_scene() -> k3d.Plot:
    rng = np.random.default_rng(0)
    xyz = (rng.normal(size=(200, 3))).astype(np.float32)
    plot = k3d.plot(grid_visible=False, menu_visibility=False)
    plot += k3d.points(xyz, point_size=0.15, color=0x4C78A8)
    return plot


ui.page_opts(title="plot.read('time') during autoplay: live vs. throttled", fillable=True)
ui.input_action_button("play", "Play both")
live_n = reactive.value(0)
throttled_n = reactive.value(0)

with ui.layout_columns():
    with ui.card():
        "Default: every tick"

        @render_k3d
        def live():
            return make_scene()

        @reactive.effect
        @reactive.event(input.play)
        def _play_live():
            live.widget.start_auto_play()

        @reactive.effect
        def _count_live():
            live.read("time")
            with reactive.isolate():
                live_n.set(live_n() + 1)

        @render.text
        def n_live():
            return f"read() fired {live_n()} times"

    with ui.card():
        "rate_delay=0.5: throttled to 2/s"

        @render_k3d(rate_policy="throttle", rate_delay=0.5)
        def throttled():
            return make_scene()

        @reactive.effect
        @reactive.event(input.play)
        def _play_throttled():
            throttled.widget.start_auto_play()

        @reactive.effect
        def _count_throttled():
            throttled.read("time")
            with reactive.isolate():
                throttled_n.set(throttled_n() + 1)

        @render.text
        def n_throttled():
            return f"read() fired {throttled_n()} times"
