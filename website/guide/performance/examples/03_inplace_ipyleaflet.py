import json
import urllib.request

import ipyleaflet as L
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="ipyleaflet: re-render vs in-place", fillable=True)

COUNTRIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
with urllib.request.urlopen(COUNTRIES_URL) as resp:
    COUNTRIES = json.load(resp)

ui.input_action_button("inplace", "Update in place (set layer.style)")
ui.input_action_button("rerender", "Force re-render (new Map)")
ui.input_action_button("toggle_visible", "Toggle layer.visible (in place)")

color_toggle = reactive.value(False)
rerender_trigger = reactive.value(0)


def style(is_red: bool) -> dict:
    return {"color": "red" if is_red else "blue", "fillOpacity": 0.3, "weight": 1}


@render_ipyleaflet
def map():
    rerender_trigger()
    with reactive.isolate():
        is_red = color_toggle()
    m = L.Map(center=(20, 0), zoom=2)
    m.add(L.GeoJSON(data=COUNTRIES, style=style(is_red), name="countries"))
    return m


def countries_layer():
    return next(lyr for lyr in map.widget.layers if lyr.name == "countries")


@reactive.effect
@reactive.event(input.inplace)
def _inplace():
    with reactive.isolate():
        is_red = not color_toggle()
    color_toggle.set(is_red)
    countries_layer().style = style(is_red)


@reactive.effect
@reactive.event(input.rerender)
def _rerender():
    with reactive.isolate():
        color_toggle.set(not color_toggle())
    rerender_trigger.set(rerender_trigger() + 1)


@reactive.effect
@reactive.event(input.toggle_visible)
def _toggle_visible():
    layer = countries_layer()
    layer.visible = not layer.visible
