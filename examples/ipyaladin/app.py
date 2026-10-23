from ipyaladin import Aladin
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipyaladin

# A few HiPS surveys hosted by CDS (https://aladin.cds.unistra.fr/hips/).
# (ui.input_select takes {value: label})
SURVEYS = {
    "https://alaskybis.unistra.fr/DSS/DSSColor": "DSS color",
    "https://alaskybis.unistra.fr/2MASS/Color": "2MASS color",
    "https://alaskybis.unistra.fr/AllWISE/Color": "allWISE color",
    "https://alaskybis.unistra.fr/GALEX/GALEXGR6_7_FUV": "GALEX far UV",
}

TARGETS = ["Crab nebula", "M31", "M51", "Orion nebula", "Sagittarius A*"]

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_selectize(
            "target",
            "Target (name or coordinates)",
            TARGETS,
            selected="Crab nebula",
        ),
        ui.input_select("survey", "Survey", SURVEYS),
        ui.input_slider("fov", "Field of view (deg)", 0.1, 60, 5, step=0.1),
        ui.p(
            "Drag the sky to pan and scroll to zoom; the readout below ",
            "tracks the viewer via reactive_read().",
        ),
    ),
    ui.card(
        ui.card_header("Sky explorer"),
        output_widget("sky"),
    ),
    ui.card(
        ui.card_header("Current view"),
        ui.output_text_verbatim("view"),
    ),
)


def server(input, output, session):
    @render_ipyaladin
    def sky():
        # The Crab nebula (M1), in ICRS degrees (a name works too, but
        # resolving it needs a round trip to CDS's Sesame service)
        return Aladin(survey=input.survey(), fov=input.fov(), target=(83.63, 22.01))

    # Point the rendered viewer at the selected target. Resolving a name
    # (e.g., "Crab nebula") to coordinates queries Sesame, which needs the
    # widget to have finished loading in the browser (hence _is_loaded)
    @reactive.effect
    def _():
        w = sky.widget
        target = input.target()
        if w and target and reactive_read(w, "_is_loaded"):
            w.target = target

    @reactive.effect
    def _():
        w = sky.widget
        if w:
            w.fov = input.fov()

    @reactive.effect
    def _():
        w = sky.widget
        if w:
            w.survey = input.survey()

    @render.text
    def view():
        target, fov = reactive_read(sky.widget, ["_target", "_fov"])
        try:
            ra, dec = (float(x) for x in target.split())
            center = f"ra={ra:.4f} deg, dec={dec:.4f} deg"
        except ValueError:
            center = target  # an unresolved name
        return f"center: {center}\nfov: {fov:.3f} deg"


app = App(app_ui, server)
