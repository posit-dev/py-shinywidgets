import ipyleaflet as L
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import reactive_read, render_ipyleaflet

ui.page_opts(title="Rate-limited reactive_read", fillable=True)

# ipyleaflet's own accessors (bounds/zoom/center/clicked/drawn_features) only
# ever fire once per gesture, so rate_policy/rate_delay has nothing to smooth
# there. It matters for reactive_read() on a trait that streams many updates
# per gesture, like a dragged marker's "location".
with ui.layout_columns(col_widths=[8, 4]):
    with ui.card():

        @render_ipyleaflet(rate_policy="throttle", rate_delay=0.5)
        def map():
            m = L.Map(center=(40.73, -73.99), zoom=14)
            m.add(L.Marker(location=(40.73, -73.99), draggable=True, name="me"))
            return m

    with ui.card():
        ui.card_header("Drag updates seen by Python (throttled to 2/s)")
        count = reactive.value(0)

        @reactive.effect
        def _count():
            req(map.widget)
            marker = next(lyr for lyr in map.widget.layers if lyr.name == "me")
            reactive_read(marker, "location")
            # isolate(): count() is both read and set here, so without
            # isolating the read this effect would depend on its own output
            # and loop forever instead of running once per throttled update
            with reactive.isolate():
                count.set(count() + 1)

        @render.code
        def n():
            return str(count())
