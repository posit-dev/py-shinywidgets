from __future__ import annotations

from astropy.table import Table
from ipyaladin import Aladin
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipyaladin

app_ui = ui.page_fluid(
    ui.input_action_button("arm_selection", "Arm selection"),
    output_widget("sky", height="400px"),
    ui.output_text("target"),
    ui.output_text("fov"),
    ui.output_text("clicked_object"),
    ui.output_text("selected_objects"),
)

# Catalog sources near the viewer's center (the Crab nebula's coordinates, so
# no name resolution is needed); one sits exactly at the target
CATALOG = Table(
    {
        "ra": [83.63, 83.70, 83.55],
        "dec": [22.01, 22.05, 21.97],
        "name": ["center", "b", "c"],
    }
)


def server(input, output, session):
    @render_ipyaladin
    def sky():
        aladin = Aladin(target=(83.63, 22.01), fov=2)
        aladin.add_table(CATALOG)
        return aladin

    # Arm rectangle selection once the user asked for it AND the viewer has
    # loaded (method calls made earlier would silently not apply)
    @reactive.effect
    def _():
        if input.arm_selection() > 0 and reactive_read(sky.widget, "_is_loaded"):
            sky.widget.selection("rectangle")

    @render.text
    def target():
        t = sky.target()
        return f"{t.ra.deg:.2f},{t.dec.deg:.2f}"

    @render.text
    def fov():
        return f"{sky.fov().deg:.4f}"

    @render.text
    def clicked_object():
        d = sky.clicked_object()
        return "None" if d is None else f"{d['ra']:.2f},{d['dec']:.2f}"

    @render.text
    def selected_objects():
        return str(sum(len(t) for t in sky.selected_objects()))


app = App(app_ui, server)
