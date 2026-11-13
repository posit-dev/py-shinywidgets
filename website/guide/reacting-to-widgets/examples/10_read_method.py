# .read(name) is the generic way to read either an accessor (by name) or,
# when the name isn't one, a bare synced trait of the rendered widget --
# without the caller needing to know ahead of time which. `map.read("zoom")`
# below returns exactly what `map.zoom()` does (an accessor wins when a name
# is both). `map.read("scroll_wheel_zoom")` falls through to
# `reactive_read(map.widget, "scroll_wheel_zoom")`, since ipyleaflet has no
# accessor for that trait. An unknown name raises, with a "did you mean"
# hint built from the renderer's accessor names -- shown live below by
# catching it and rendering `str(exc)`.
from ipyleaflet import Map
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title=".read()")

with ui.card(height="350px"):
    ui.card_header("Pan or zoom the map")

    @render_ipyleaflet
    def map():
        return Map(center=(45.5, -122.6), zoom=9, scroll_wheel_zoom=True)


with ui.layout_columns():
    with ui.card():
        ui.card_header('map.read("zoom") -- an accessor, by name')

        @render.code
        def read_zoom():
            return str(map.read("zoom"))

    with ui.card():
        ui.card_header('map.read("scroll_wheel_zoom") -- a bare trait, no accessor')

        @render.code
        def read_trait():
            return str(map.read("scroll_wheel_zoom"))

with ui.card():
    ui.card_header('map.read("zooom") -- unknown name raises, with a hint')

    @render.code
    def read_typo():
        try:
            return str(map.read("zooom"))
        except AttributeError as e:
            return str(e)
