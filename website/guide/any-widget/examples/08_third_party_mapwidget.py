# Needs: uv run --no-sync --with mapwidget python -m shiny run 08_third_party_mapwidget.py
#
# mapwidget (https://github.com/opengeos/mapwidget) has no dedicated
# shinywidgets renderer -- plain `render_widget` is enough, because
# mapwidget.maplibre.Map is already an ipywidgets.Widget subclass; there is
# nothing to coerce. This is the common case for "my widget isn't on the
# roster": if `pip install <library>` gives you an anywidget/ipywidgets class
# directly, `@render_widget` just works.
import mapwidget.maplibre as maplibregl
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_widget

ui.page_opts(title="A third-party widget with no dedicated renderer", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("mapwidget.maplibre.Map (click the map)")
        ui.input_action_button("dark", "Switch to dark style")

        @render_widget
        def map():
            return maplibregl.Map(center=[40.7128, -74.0060], zoom=10)

        # Python -> JS state changes on this widget are forwarded with
        # `add_call(method, args)`, not by assigning a trait (assigning
        # `map.widget.center = ...` changes the Python-side trait but never
        # moves the rendered map -- documented, verified upstream behavior).
        # A call made before the widget's real comm opens -- even from
        # inside the render function above -- is no longer dropped (see
        # "Reacting to user interaction"); the button here is just this toy
        # app's trigger for "restyle on demand," not a workaround.
        @reactive.effect
        @reactive.event(input.dark)
        def _dark_style():
            map.widget.add_call(
                "setStyle", ["https://tiles.openfreemap.org/styles/fiord"]
            )

    with ui.card():
        ui.card_header('map.read("clicked_latlng") / map.read("zoom")')

        @render.code
        def state_out():
            lat, lng = map.read("clicked_latlng")
            zoom = map.read("zoom")
            clicked = "nowhere yet" if lat is None else f"({lat:.3f}, {lng:.3f})"
            return f"zoom: {zoom:.1f}\nlast click: {clicked}"
