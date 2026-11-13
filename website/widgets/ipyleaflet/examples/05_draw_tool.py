import ipyleaflet as L
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Draw on the map", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card():

        @render_ipyleaflet
        def map():
            m = L.Map(center=(40.73, -73.99), zoom=13)
            m.add(L.DrawControl(polygon={"shapeOptions": {"color": "#2a7fff"}}))
            return m

    with ui.card():
        ui.card_header("map.drawn_features()")

        @render.code
        def features():
            feats = map.drawn_features()
            kinds = [f["geometry"]["type"] for f in feats]
            return f"{len(feats)} shape(s)\n" + "\n".join(kinds)
