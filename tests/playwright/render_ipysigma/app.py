from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipysigma

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_action_button("rerender_last", "Rerender last graph"),
    ui.output_text("render_count"),
    ui.output_text("render_last_count"),
    ui.output_text("selected"),
    ui.card(output_widget("fills"), id="fill_card", height="400px"),
    ui.card(output_widget("fixed_output", height="350px"), id="fixed_card"),
    ui.card(output_widget("fixed_widget"), id="widget_card", height="500px"),
    ui.card(output_widget("not_fillable", fillable=False), id="not_fillable_card"),
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

    @render.text
    def render_last_count():
        return str(input.rerender_last())

    @render_ipysigma
    def fills():
        counter.get()
        return nx.karate_club_graph()

    @render.text
    def selected():
        return str(reactive_read(fills.widget, "selected_node"))

    @render_ipysigma
    def fixed_output():
        return nx.karate_club_graph()

    @render_ipysigma
    def fixed_widget():
        input.rerender_last()
        return Sigma(nx.karate_club_graph(), height=300)

    @render_ipysigma
    def not_fillable():
        return nx.karate_club_graph()


app = App(app_ui, server)
