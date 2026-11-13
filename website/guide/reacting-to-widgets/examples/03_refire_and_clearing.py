# Re-fire and clearing semantics, using two plotly accessors on the same
# figure. An effect counts how many times each accessor's value actually
# changes (using `reactive.isolate()` so the counter doesn't depend on
# itself; see "Writing back" in the Updating in place article for why that
# matters):
#
# - `clicked()` dedupes by value (input priority): clicking the SAME point
#   twice publishes the same value twice, but the counter doesn't advance on
#   the second click. A double-click that lands on a MARKER re-fires
#   `clicked()` (the second click of the pair is a normal click on that
#   point) -- it does not clear. A double-click that lands on the BACKGROUND
#   clears `clicked()` back to None (plotly's own "double-click resets the
#   view" gesture).
# - `double_clicked()` is a *pulse*: it fires `True` on every double-click on
#   the background and never clears, so two separate double-clicks there
#   both advance the counter even though the displayed value never changes
#   from `True` -- a pulse re-fires readers on an unchanged value by design,
#   the opposite of `clicked()`'s dedup.
import plotly.express as px
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.iris().reset_index(drop=True)

ui.page_opts(title="Re-fire and clearing", fillable=True)

fires = reactive.value(0)
pulses = reactive.value(0)

with ui.layout_columns(col_widths=[6, 3, 3]):
    with ui.card(full_screen=True):

        @render_plotly
        def plot():
            return px.scatter(df, x="sepal_width", y="sepal_length", custom_data=[df.index])

    with ui.card():
        ui.card_header("plot.clicked()")

        @reactive.effect
        def _count_fires():
            plot.clicked()  # depend on it
            with reactive.isolate():
                fires.set(fires() + 1)

        @render.code
        def clicked_out():
            pts = plot.clicked()
            state = "None" if pts is None else f"point_index={pts['point_index'].iloc[0]}"
            return f"fires so far: {fires()}\nclicked(): {state}"

    with ui.card():
        ui.card_header("plot.double_clicked() -- a pulse")

        @reactive.effect
        def _count_pulses():
            plot.double_clicked()  # depend on it
            with reactive.isolate():
                pulses.set(pulses() + 1)

        @render.code
        def double_clicked_out():
            return f"fires so far: {pulses()}\ndouble_clicked(): {plot.double_clicked()}"
