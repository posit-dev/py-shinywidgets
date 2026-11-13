from ipyaladin import Aladin
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import reactive_read, render_ipyaladin

# A few HiPS surveys hosted by CDS (https://aladin.cds.unistra.fr/hips/)
SURVEYS = {
    "https://alaskybis.unistra.fr/DSS/DSSColor": "DSS color (optical)",
    "https://alaskybis.unistra.fr/2MASS/Color": "2MASS color (infrared)",
    "https://alaskybis.unistra.fr/AllWISE/Color": "allWISE color (mid-IR)",
}
CMAPS = ["native", "viridis", "cubehelix", "grayscale"]

ui.page_opts(title="Switch surveys and color maps", fillable=True)
ui.input_select("survey", "Survey", SURVEYS)
ui.input_select("cmap", "Color map", CMAPS)

with ui.card(full_screen=True):

    @render_ipyaladin
    def sky():
        return Aladin(target=(83.822, -5.391), fov=2, survey=list(SURVEYS)[0])  # M42

    # `survey` is a plain synced trait, so it updates as soon as it's set
    @reactive.effect
    def _():
        w = sky.widget
        if w:
            w.survey = input.survey()

    # set_color_map() sends a one-off message rather than syncing a trait,
    # so it's lost if sent before the browser has loaded -- gate on _is_loaded
    @reactive.effect
    def _():
        w = sky.widget
        if w and reactive_read(w, "_is_loaded") and input.cmap() != "native":
            w.set_color_map(input.cmap())

    @render.text
    def label():
        return f"{SURVEYS[input.survey()]}, {input.cmap()} color map"
