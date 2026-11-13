import leafmap
from shiny.express import render, ui
from shinywidgets import render_leafmap

ui.page_opts(title="leafmap zoom() and center()", fillable=True)

with ui.layout_columns(col_widths=(9, 3)):

    @render_leafmap
    def map():
        m = leafmap.Map(center=(47.62, -122.33), zoom=11)
        m.add_basemap("OpenTopoMap")
        return m

    with ui.card():
        ui.card_header("Live camera")

        @render.code
        def camera():
            # Both fire on every pan/zoom gesture and whenever Python sets
            # map.widget.zoom/center; neither is rate-limited
            lat, lng = map.center()
            return f"zoom:   {map.zoom():.1f}\ncenter: ({lat:.3f}, {lng:.3f})"
