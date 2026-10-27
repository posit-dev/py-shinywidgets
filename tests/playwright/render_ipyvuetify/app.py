from __future__ import annotations

import os

import ipyvuetify as v
import traitlets
from ipyvue import VueTemplate
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

# ipyvuetify's module-level theme is a process-wide singleton, shared by every
# widget tree and session
v.theme.dark = True


class Labeled(VueTemplate):
    # Loaded through ipyvue's process-wide template registry
    template_file = os.path.join(os.path.dirname(__file__), "component.vue")
    label = traitlets.Unicode("").tag(sync=True)


app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("btn"),
    output_widget("tmpl"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_widget
    def btn():
        n = counter.get()
        return v.Container(children=[v.Btn(children=[f"vuetify button {n}"])])

    @render_widget
    def tmpl():
        n = counter.get()
        return Labeled(label=f"render {n}")


app = App(app_ui, server)
