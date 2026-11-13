from __future__ import annotations

from geolibre import Map
from shiny import reactive, req
from shiny import ui as core_ui
from shiny.express import render, ui

from shinywidgets import render_geolibre

ui.page_opts(title="Click a state for details", fillable=True)

US_STATES = (
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/"
    "master/data/geojson/us-states.json"
)

# The most recent click, including the feature(s) under the cursor (populated
# because Identify is armed below) -- set from geolibre's on_click event.
last_click = reactive.value(None)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_geolibre
        def map():
            m = Map(center=(-98.5, 39.8), zoom=4)
            layer_id = m.add_choropleth(US_STATES, column="density", name="Population density")
            m.set_identify(layer_id)  # include feature properties in click events
            m.on_click(lambda e: last_click.set(e))
            return m

    with ui.card():
        ui.card_header("Clicked state")

        @render.ui
        def detail():
            event = req(last_click())
            features = event.get("features") or []
            if not features:
                return core_ui.value_box("No state here", "click land to select one")
            props = features[0]["properties"]
            return core_ui.value_box(props["name"], f"{props['density']:.1f} people/sq mi")
