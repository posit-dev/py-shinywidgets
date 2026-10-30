from __future__ import annotations

from ipyniivue import NiiVue, Volume
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_niivue

app_ui = ui.page_fluid(
    output_widget("brain", height="400px"),
    ui.output_text("location"),
    ui.output_text("eval_count"),
)


def server(input, output, session):
    n_evals = [0]

    @render_niivue
    def brain():
        nv = NiiVue()
        nv.load_volumes(
            [Volume(url="https://niivue.com/demos/images/mni152.nii.gz")]
        )
        return nv

    @reactive.calc
    def loc():
        n_evals[0] += 1
        return brain.location()

    @render.text
    def location():
        value = loc()
        if value is None:
            return "None"
        return ",".join(f"{v:.1f}" for v in value["mm"])

    @render.text
    def eval_count():
        loc()
        return str(n_evals[0])


app = App(app_ui, server)
