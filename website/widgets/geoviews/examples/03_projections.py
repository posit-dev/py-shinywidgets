# Web Mercator (the default, needed for tile basemaps) vs. a real cartographic
# projection. Swapping `projection=` reshapes the coastlines and repositions
# every point -- there is no "zoom into a Robinson map" the way there is with
# tiles, since tiles only exist pre-rendered in Web Mercator.
import cartopy.crs as ccrs
import geoviews as gv
import geoviews.feature as gf
import holoviews as hv
import numpy as np
from shiny.express import ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

rng = np.random.default_rng(0)
# A few hundred points scattered near shipping lanes, for visual texture
lons = rng.uniform(-180, 180, 300)
lats = rng.uniform(-60, 75, 300)

ui.page_opts(title="Web Mercator vs. a real projection", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Default: Web Mercator, with tiles")

        @render_holoviews
        def mercator():
            pts = gv.Points((lons, lats)).opts(color="firebrick", size=3, alpha=0.6)
            return (gv.tile_sources.OSM * pts).opts(responsive=True)

    with ui.card(full_screen=True):
        ui.card_header("projection=ccrs.Robinson(), no tiles")

        @render_holoviews
        def robinson():
            pts = gv.Points((lons, lats)).opts(color="firebrick", size=3, alpha=0.6)
            overlay = gf.coastline * gf.borders * pts
            return overlay.opts(
                "Points",
                responsive=True,
            ).opts(
                projection=ccrs.Robinson(), global_extent=True, title="Robinson"
            )
