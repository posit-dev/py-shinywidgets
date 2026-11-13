# Four different "before the first interaction" states, across four widgets:
#
# - k3d's camera() CANCELS (like `req(False)`) until the browser reports a
#   camera -- the output renders nothing at all, same as a widget that
#   hasn't rendered. No `req()` needed; there is nothing to check.
# - ipyleaflet's clicked() returns None until the first click.
#   `req(map.clicked())` is the pattern for waiting on it.
# - bokeh's selected() returns `[]` (not None) until the first tap/box
#   select -- an empty list either means "nothing selected yet" or "a
#   selection that caught nothing"; both read the same way.
# - altair's selected() is seeded the moment the chart renders: it is never
#   None or empty-as-a-sentinel -- an untouched selection is itself a real,
#   usable (empty) Vega-Lite object. Checking `.value` (or `selected_rows()`,
#   which returns an empty frame) is how you tell "untouched" from "selected
#   nothing" apart -- no `req()` needed either.
import altair as alt
import numpy as np
import pandas as pd
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from ipyleaflet import Map
from k3d import points
from shiny.express import render, ui

from shinywidgets import render_altair, render_bokeh, render_ipyleaflet, render_k3d

df = pd.DataFrame({"x": range(10), "y": [i**2 % 7 for i in range(10)]})
bokeh_source = ColumnDataSource(
    data=dict(x=list(range(10)), y=[i**2 % 7 for i in range(10)])
)

ui.page_opts(title="Before the first interaction", fillable=True)

with ui.layout_columns():
    with ui.card():
        ui.card_header("k3d: camera() -- cancels until ready")

        @render_k3d
        def plot():
            return points(np.random.normal(size=(200, 3)).astype("float32"))

        @render.code
        def camera_out():
            return str([round(v, 1) for v in plot.camera()])

    with ui.card():
        ui.card_header("ipyleaflet: clicked() -- None until the first click")

        @render_ipyleaflet
        def map():
            return Map(center=(45.5, -122.6), zoom=9)

        @render.code
        def clicked_out():
            pt = map.clicked()
            return "None (click the map)" if pt is None else str(pt["coordinates"])

    with ui.card():
        ui.card_header("bokeh: selected() -- [] until the first selection")

        @render_bokeh
        def bplot():
            p = figure(tools="tap,box_select,reset", title="Tap or box-select points")
            p.scatter("x", "y", source=bokeh_source, size=14)
            return p

        @render.code
        def bokeh_out():
            return f"selected(): {bplot.selected()}"

    with ui.card():
        ui.card_header("altair: selected() -- never None")

        @render_altair
        def chart():
            brush = alt.selection_interval(name="brush")
            return (
                alt.Chart(df)
                .mark_point(size=100)
                .encode(x="x", y="y")
                .add_params(brush)
            )

        @render.code
        def selected_out():
            sel = chart.selected("brush")
            return f"value={sel.value!r}\nselected_rows: {len(chart.selected_rows('brush'))} row(s)"
