import leafmap.maplibregl as lmgl
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_leafmap

ui.page_opts(title="leafmap's maplibre backend", fillable=True)

with ui.layout_columns(col_widths=(9, 3)):

    @render_leafmap
    def map():
        return lmgl.Map(center=(-122.42, 37.77), zoom=11, style="positron")

    with ui.card():
        ui.card_header("map.read(), not accessors")

        @render.code
        def view_state():
            # This backend isn't an ipyleaflet.Map, so map.zoom()/map.bounds()/etc.
            # raise TypeError; read maplibre's own traits with map.read()
            vs = map.read("view_state")
            req(vs)  # {} until the browser's first moveend/zoomend
            c = vs["center"]
            return (
                f"center: ({c['lng']:.3f}, {c['lat']:.3f})\n"
                f"zoom:   {vs['zoom']:.1f}\n"
                f"bearing/pitch: {vs['bearing']:.0f}, {vs['pitch']:.0f}"
            )

        @render.code
        def accessor_error():
            try:
                map.zoom()
            except TypeError as e:
                return f"map.zoom() raises:\n{e}"
