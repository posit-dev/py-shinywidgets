# Updating a widget in place from an effect, instead of re-rendering it.
# Each click on the map adds a marker at that spot via `map.widget.add(...)`
# -- the SAME Map instance keeps running, so whatever the user already
# panned/zoomed to survives. Re-rendering the map from the click (e.g. by
# making `map()` read a `reactive.value` that the effect sets) would send a
# brand new Map to the browser and reset the zoom/center every time.
#
# The counter is bumped with `reactive.isolate()`. Without it, this effect
# would read `clicks()` (to compute `clicks() + 1`) AND set it in the same
# run, so `clicks.set(...)` would invalidate the very effect that's running
# -- which reschedules itself, reads `clicks()` again, sets it again, and
# never stops: a silent infinite loop that pins a CPU core and freezes the
# whole app (no error, no output change -- see the article text for how to
# recognize this).
from ipyleaflet import Map, Marker
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Writing back", fillable=True)

clicks = reactive.value(0)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Click the map to drop a marker (zoom/pan are preserved)")

        @render_ipyleaflet
        def map():
            return Map(center=(45.5, -122.6), zoom=9)

    with ui.card():
        ui.card_header("Markers added")

        @reactive.effect
        def _add_marker():
            pt = map.clicked()
            if pt is None:
                return
            lat, lng = pt["coordinates"]
            map.widget.add(Marker(location=(lat, lng), draggable=False))
            with reactive.isolate():
                clicks.set(clicks() + 1)

        @render.code
        def count_out():
            return f"{clicks()} marker(s) added"
