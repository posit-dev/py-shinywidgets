import ipyleaflet as L
from shiny.express import ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Basemaps", fillable=True)

with ui.card():

    @render_ipyleaflet
    def map():
        m = L.Map(center=(40.73, -73.99), zoom=12)  # default basemap: OSM Mapnik
        mapnik = m.layers[0]

        satellite = L.basemap_to_tiles(L.basemaps.Esri.WorldImagery)
        satellite.base, satellite.name = True, "Satellite"
        m.add(satellite)

        topo = L.basemap_to_tiles(L.basemaps.OpenTopoMap)
        topo.base, topo.name = True, "Topo"
        m.add(topo)

        m.add(L.LayersControl(position="topright"))

        # Every base=True layer stays visible until the user picks one in the
        # control (ipyleaflet doesn't enforce exclusivity up front), so
        # whichever was added last is what actually shows. Re-add the
        # intended default last so it's the one on top initially.
        m.remove(mapnik)
        m.add(mapnik)
        return m
