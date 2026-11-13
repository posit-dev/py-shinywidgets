import numpy as np
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_widget

from sparkline_widget import Sparkline

rng = np.random.default_rng(4)
DATA = list(rng.normal(size=40).cumsum())


def nearest_point(output, data):
    """
    Accessor-like helper: turns a raw `clicked_index` trait into the actual
    data point. Custom widgets don't come with built-in accessors like
    `render_plotly`'s `clicked()` -- this is the pattern for writing your
    own: wrap `.read()` in a function returning a `@reactive.calc`, so every
    call site gets the same typed value instead of repeating the
    index-to-row lookup.
    """

    @reactive.calc
    def _():
        idx = output.read("clicked_index")
        return None if idx is None else data[idx]

    return _


ui.page_opts(title="A reusable accessor-like helper, and rate limiting", fillable=True)
ui.markdown("Drag across each sparkline (slowly, over ~1 second) and compare the counts.")

with ui.layout_columns():
    with ui.card():
        ui.card_header("default: .read() fires on every drag update")

        @render_widget
        def spark():
            return Sparkline(values=DATA)

        n_default = reactive.value(0)

        @reactive.effect
        def _count_default():
            spark.read("clicked_index")
            with reactive.isolate():
                n_default.set(n_default() + 1)

        @render.code
        def out_default():
            return f"fired {n_default()} times"

    with ui.card():
        ui.card_header("render_widget(rate_policy='debounce', rate_delay=0.5)")

        @render_widget(rate_policy="debounce", rate_delay=0.5)
        def spark_slow():
            return Sparkline(values=DATA)

        n_slow = reactive.value(0)

        @reactive.effect
        def _count_slow():
            spark_slow.read("clicked_index")
            with reactive.isolate():
                n_slow.set(n_slow() + 1)

        @render.code
        def out_slow():
            return f"fired {n_slow()} times"

with ui.card():
    ui.card_header("nearest_point(spark, DATA)() -- the helper in use")

    point = nearest_point(spark, DATA)

    @render.code
    def point_out():
        p = point()
        return "drag the left sparkline" if p is None else f"value at that index: {p:.3f}"
