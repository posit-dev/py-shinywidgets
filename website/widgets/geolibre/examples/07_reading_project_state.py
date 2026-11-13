from __future__ import annotations

import json

from geolibre import Map
from shiny import render
from shiny.express import ui

from shinywidgets import render_geolibre

ui.page_opts(title="Reading the live project", fillable=True)

US_STATES = (
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/"
    "master/data/geojson/us-states.json"
)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_geolibre
        def map():
            m = Map(center=(-98.5, 39.8), zoom=4)
            m.add_geojson(US_STATES, name="US States", fillColor="#2a6fdb", fillOpacity=0.25)
            return m

    with ui.card():
        ui.card_header("project.mapView and layer names")

        @render.code
        def view_info():
            # Invalidates on every pan and zoom -- the whole project re-syncs,
            # not just the view, so keep downstream consumers cheap (see
            # "Rate limiting" below). "bbox" is filled in once the browser's
            # first sync lands (a moment after the app boots), so treat it as
            # optional rather than indexing it directly.
            project = map.read("project")
            view = project["mapView"]
            bbox = view.get("bbox")
            return json.dumps(
                {
                    "center": [round(c, 2) for c in view["center"]],
                    "zoom": round(view["zoom"], 2),
                    "bbox": [round(b, 2) for b in bbox] if bbox else None,
                    "layers": [layer["name"] for layer in project["layers"]],
                },
                indent=2,
            )
