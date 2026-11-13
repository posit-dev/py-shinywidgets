import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
LAYOUTS = ["cose", "concentric", "breadthfirst", "dagre"]

ui.page_opts(title="Layouts", fillable=True)
ui.input_select("layout", "Layout", LAYOUTS)

with ui.card(full_screen=True):

    @render_ipycytoscape
    def network():
        widget = CytoscapeWidget(G)
        with reactive.isolate():
            widget.set_layout(name=input.layout())
        return widget

    @reactive.effect
    def _():
        # Re-run the chosen layout in place; the graph is never re-rendered
        network.widget.set_layout(name=input.layout())
