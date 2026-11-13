from __future__ import annotations

from geolibre import Map
from shiny import reactive
from shiny.express import input, ui

from shinywidgets import render_geolibre

ui.page_opts(title="Styling + popups", fillable=True)

US_STATES = (
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/"
    "master/data/geojson/us-states.json"
)

with ui.sidebar():
    ui.input_slider("opacity", "Fill opacity", 0, 1, 0.6, step=0.1)
    ui.input_select("color", "Fill color", ["#2a6fdb", "#e3342f", "#38a169"])

with ui.card(full_screen=True):

    @render_geolibre
    def map():
        m = Map(center=(-98.5, 39.8), zoom=4)
        layer_id = m.add_choropleth(US_STATES, column="density", name="Population density")
        layer = m.get_layer(layer_id)
        # A click opens a popup with just these two fields, titled by name
        m.set_popup(
            layer,
            [
                {"field": "name", "label": "State"},
                {"field": "density", "label": "Density", "kind": "number", "decimals": 1},
            ],
            title="name",
            show_feature_id=False,
        )
        m.set_identify(layer)  # arm Identify so a click opens the popup
        return m


# Restyling an existing layer updates the live map in place -- no re-render
@reactive.effect
def _():
    layer = map.widget.find_layer("Population density")
    layer.opacity = input.opacity()
    layer.set_style(fillColor=input.color())
