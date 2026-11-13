# Run: uv run --with mocpy shiny run 05_footprints_moc.py
# (mocpy builds the MOC; it isn't needed for the rest of this guide)
import astropy.units as u
from ipyaladin import Aladin
from mocpy import MOC
from shiny.express import ui
from shinywidgets import render_ipyaladin

TARGET = (83.82, -5.39)  # Orion Nebula (M42)

ui.page_opts(title="Footprints and MOCs", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("A MOC search region and an instrument footprint over M42")

    @render_ipyaladin
    def sky():
        aladin = Aladin(target=TARGET, fov=1.5)
        moc = MOC.from_cone(
            lon=TARGET[0] * u.deg, lat=TARGET[1] * u.deg, radius=0.2 * u.deg, max_depth=9
        )
        aladin.add_moc(moc, color="#06d6a0", opacity=0.4, name="search region")
        aladin.add_graphic_overlay_from_stcs(
            "Circle ICRS 83.82 -5.39 0.35", color="#ef476f", name="instrument footprint"
        )
        return aladin
