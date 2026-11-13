# The renderer's rate_policy/rate_delay kwargs only govern accessors that
# declare a DEFAULT rate policy (plus reactive_read() on the root widget).
# plotly's selecting() debounces by default, so rate_delay actually changes
# its behavior; k3d's camera() declares no default rate policy at all, so
# the same kwargs are silently a no-op for it -- every raw update publishes
# immediately either way (k3d's own JS throttles camera updates to roughly
# once per 200ms, independent of anything shinywidgets does). Each panel
# counts how many times the accessor's value actually changes during one
# slow drag.
import k3d
import numpy as np
import plotly.express as px
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_k3d, render_plotly

df = px.data.iris().reset_index(drop=True)


def counter():
    n = reactive.value(0)

    def bump():
        with reactive.isolate():
            n.set(n() + 1)

    return n, bump


def k3d_points():
    rng = np.random.default_rng(0)
    plot = k3d.plot()
    plot += k3d.points(
        rng.random((200, 3), dtype=np.float32), point_size=0.05, color=0xFF0000
    )
    return plot


ui.page_opts(title="rate_policy / rate_delay", fillable=True)
ui.markdown(
    "Drag a box slowly on each plotly figure (~1 second), and orbit-drag each "
    "k3d plot slowly (~1 second), then read the counts."
)

with ui.layout_columns():
    with ui.card():
        ui.card_header("plotly selecting(): default debounce (250ms)")

        @render_plotly
        def plot_default():
            return px.scatter(df, x="sepal_width", y="sepal_length").update_layout(
                dragmode="select"
            )

        n_default, bump_default = counter()

        @reactive.effect
        def _():
            plot_default.selecting()
            bump_default()

        @render.code
        def out_default():
            return f"selecting() fired {n_default()} times"

    with ui.card():
        ui.card_header("plotly selecting(rate_delay=0): every raw update")

        @render_plotly(rate_delay=0)
        def plot_fast():
            return px.scatter(df, x="sepal_width", y="sepal_length").update_layout(
                dragmode="select"
            )

        n_fast, bump_fast = counter()

        @reactive.effect
        def _():
            plot_fast.selecting()
            bump_fast()

        @render.code
        def out_fast():
            return f"selecting() fired {n_fast()} times"

    with ui.card():
        ui.card_header("k3d camera(): no default -- rate_delay=0 here")

        @render_k3d(rate_delay=0, height="300px")
        def plot_a():
            return k3d_points()

        n_a, bump_a = counter()

        @reactive.effect
        def _():
            plot_a.camera()
            bump_a()

        @render.code
        def out_a():
            return f"camera() fired {n_a()} times"

    with ui.card():
        ui.card_header("k3d camera(rate_delay=2): same renderer kwarg, no effect")

        @render_k3d(rate_delay=2, height="300px")
        def plot_b():
            return k3d_points()

        n_b, bump_b = counter()

        @reactive.effect
        def _():
            plot_b.camera()
            bump_b()

        @render.code
        def out_b():
            return f"camera() fired {n_b()} times"
