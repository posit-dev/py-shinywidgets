# Kept vs. re-seeded, side by side, on the same map: `clicked()` is
# *user-interaction state* -- it keeps the last click until the user clicks
# the new map. `zoom()`/`center()` are *inherent widget state* -- each
# re-render re-seeds them from the freshly built Map's own construction-time
# zoom/center. Click the map, pan and zoom it, then click "Re-render":
# clicked() is unchanged; zoom()/center() snap back to zoom=9.
#
# A kept payload can describe the PREVIOUS render's widget. If a re-render
# replaces the data a click's payload indexed into (a point index, a row
# position), the retained value can silently point at something else after
# the re-render -- see plot.clicked()'s docstring (plotly) and
# ipydatagrid's edited_cell() for the same caveat: prefer an ID-keyed lookup
# over a positional one whenever the data itself can change across a render.
from ipyleaflet import Map
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Across re-renders", fillable=True)
ui.input_action_button("rerender", "Re-render map")

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click, pan, and zoom, then click Re-render")

        @render_ipyleaflet
        @reactive.event(input.rerender, ignore_none=False)
        def map():
            return Map(center=(45.5, -122.6), zoom=9)

    with ui.card():
        ui.card_header("map.clicked() -- kept across re-render")

        @render.code
        def clicked_out():
            pt = map.clicked()
            return "None (click the map)" if pt is None else str(pt["coordinates"])

    with ui.card():
        ui.card_header("map.zoom() / map.center() -- re-seeded every render")

        @render.code
        def zoom_out():
            return f"zoom={map.zoom()}\ncenter={map.center()}"
