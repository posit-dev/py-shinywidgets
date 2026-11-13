from ipyaladin import Aladin
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyaladin

# Values are "ra dec" strings (parsed locally, no network call); a plain
# name like "M31" also works on the setter, but it resolves via a CDS web
# service and adds network latency -- fine for an occasional user-driven
# search, less fine for a value a dropdown sets on every click
TARGETS = {
    "10.685 41.269": "Andromeda Galaxy (M31)",
    "83.822 -5.391": "Orion Nebula (M42)",
    "56.75 24.12": "Pleiades (M45)",
    "83.633 22.014": "Crab Nebula (M1)",
}

ui.page_opts(title="Navigate by name", fillable=True)
ui.input_select("target", "Go to", TARGETS)

with ui.card(full_screen=True):

    @render_ipyaladin
    def sky():
        return Aladin(target=(10.685, 41.269), fov=3)

    @reactive.effect
    def _():
        w = sky.widget
        if w:
            w.target = input.target()

    @render.code
    def center():
        t = sky.target()
        return f"ra={t.ra.deg:.3f} dec={t.dec.deg:.3f}  fov={sky.fov().deg:.3f} deg"
