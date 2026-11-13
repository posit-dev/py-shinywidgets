import ipyvolume as ipv
import numpy as np
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import reactive_read, render_ipyvolume

# camera() has no default rate policy: a drag already collapses to one trait
# update at the end of the orbit, so there's nothing bursty to coalesce.
# rate_policy/rate_delay still apply to plain reactive_read() calls on the
# widget -- useful for a trait that *does* update repeatedly, like the canvas
# size while its container is being resized.
ui.page_opts(title="Rate limiting", fillable=True)

rng = np.random.default_rng(0)
pts = rng.normal(size=(3, 300))


def make_fig():
    fig = ipv.figure()
    ipv.scatter(*pts, size=1, marker="sphere", color="tomato")
    return fig


with ui.layout_columns():
    with ui.card():
        ui.card_header("Unthrottled")

        @render_ipyvolume
        def plot_live():
            return make_fig()

    with ui.card():
        ui.card_header("Debounced 500ms")

        @render_ipyvolume(rate_policy="debounce", rate_delay=0.5)
        def plot_debounced():
            return make_fig()


live_count = reactive.value(0)
debounced_count = reactive.value(0)


@render.code
def live_recomputes():
    reactive_read(plot_live.widget, "width")
    with reactive.isolate():
        n = live_count.get() + 1
        live_count.set(n)
    return f"unthrottled recomputes: {n}"


@render.code
def debounced_recomputes():
    reactive_read(plot_debounced.widget, "width")
    with reactive.isolate():
        n = debounced_count.get() + 1
        debounced_count.set(n)
    return f"debounced recomputes: {n}"
