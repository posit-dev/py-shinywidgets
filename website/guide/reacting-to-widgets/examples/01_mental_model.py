# Accessors read like inputs. This renders the same ipyleaflet map twice,
# side by side: the left card reads `map.zoom()` and `map.center()` -- the
# renderer's accessors -- and the right card reads the identical state with
# the lower-level primitive underneath them, `reactive_read(map.widget, "zoom")`.
# Both update together on every pan or zoom; the accessor adds nothing here but
# a name, a docstring, and (for other accessors) a default rate policy -- see
# the next examples for cases where that default actually matters.
from ipyleaflet import Map
from shiny.express import render, ui
from shinywidgets import reactive_read, render_ipyleaflet

ui.page_opts(title="Accessors vs. reactive_read", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("The map")

        @render_ipyleaflet
        def map():
            return Map(center=(45.5, -122.6), zoom=10)

    with ui.card():
        ui.card_header("map.zoom() / map.center() -- the accessor")

        @render.code
        def via_accessor():
            return f"zoom={map.zoom()}\ncenter={map.center()}"

    with ui.card():
        ui.card_header('reactive_read(map.widget, ["zoom", "center"]) -- the primitive')

        @render.code
        def via_reactive_read():
            zoom, center = reactive_read(map.widget, ["zoom", "center"])
            return f"zoom={zoom}\ncenter={center}"
