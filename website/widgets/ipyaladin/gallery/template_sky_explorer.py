# Sky explorer -- a small, adaptable starting point for an ipyaladin app.
# template | ~85 lines | run: uv run shiny run template_sky_explorer.py
# Data: 6 bright deep-sky objects, hardcoded real coordinates.
from __future__ import annotations

from astropy.table import Table
from ipyaladin import Aladin
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import reactive_read, render_ipyaladin

OBJECTS = Table(
    {
        "name": ["Andromeda Galaxy", "Orion Nebula", "Pleiades", "Crab Nebula", "Whirlpool Galaxy", "Ring Nebula"],
        "ra": [10.685, 83.822, 56.75, 83.633, 202.47, 283.396],
        "dec": [41.269, -5.391, 24.12, 22.014, 47.195, 33.029],
        "type": ["Galaxy", "Nebula", "Open cluster", "Supernova remnant", "Galaxy", "Planetary nebula"],
    }
)

SURVEYS = {
    "https://alaskybis.unistra.fr/DSS/DSSColor": "DSS color (optical)",
    "https://alaskybis.unistra.fr/2MASS/Color": "2MASS color (infrared)",
}

ui.page_opts(title="Sky explorer", fillable=True)

with ui.sidebar():
    ui.input_select(
        "target", "Go to", {row["name"]: row["name"] for row in OBJECTS}, selected="Pleiades"
    )
    ui.input_select("survey", "Survey", SURVEYS)
    ui.p(
        "Drag to pan, scroll to zoom, click a marker for details.",
        class_="text-muted small",
    )

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_ipyaladin
        def sky():
            aladin = Aladin(target=(56.75, 24.12), fov=4, survey=list(SURVEYS)[0])
            aladin.add_table(OBJECTS, shape="circle", source_size=16, color="#ffd166")
            return aladin

    with ui.card():
        ui.card_header("Clicked object")

        @render.code
        def detail():
            clicked = sky.clicked_object()
            if clicked is None:
                return "Click a marker in the sky to inspect it."
            d = clicked["data"]
            return "\n".join(f"{k}: {v}" for k, v in d.items())

        ui.card_header("Current view")

        @render.text
        def view():
            t = sky.target()
            return f"ra={t.ra.deg:.2f}  dec={t.dec.deg:.2f}  fov={sky.fov().deg:.2f} deg"


# Fly to the selected object (in place: no re-render, no tile re-fetch)
@reactive.effect
def _go_to_target():
    w = sky.widget
    name = input.target()
    if w is None or not reactive_read(w, "_is_loaded"):
        return
    row = next(r for r in OBJECTS if r["name"] == name)
    with reactive.isolate():
        w.target = f"{row['ra']} {row['dec']}"
        w.fov = 4


# Re-skin the imagery in place
@reactive.effect
def _switch_survey():
    w = sky.widget
    if w:
        w.survey = input.survey()
