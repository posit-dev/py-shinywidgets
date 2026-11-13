import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
CHARACTERS = sorted(G.nodes)
STYLE = [
    {"selector": "node", "style": {"background-color": "#447099"}},
    {"selector": "node.path", "style": {"label": "data(id)", "border-width": 3}},
    {"selector": "edge.path", "style": {"line-color": "#e15759", "width": 5}},
]

ui.page_opts(title="Shortest path, drawn in place", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_ipycytoscape
        def network():
            widget = CytoscapeWidget(G)
            widget.set_style(STYLE)
            widget.set_layout(name="cose")
            return widget

    with ui.card():
        ui.input_selectize(
            "ends",
            "Shortest path between",
            CHARACTERS,
            multiple=True,
            options={"maxItems": 2},
        )

        @render.ui
        def info():
            if len(input.ends()) != 2:
                return ui.p("Pick two characters.")
            return ui.p(" → ".join(path()))


@reactive.calc
def path() -> list[str]:
    ends = input.ends()
    if len(ends) != 2:
        return []
    return nx.shortest_path(G, *ends)


@reactive.effect
def _():
    # No re-render and no relayout: only each element's classes change
    p = set(path())
    on_path_edges = set(zip(path(), path()[1:])) | set(zip(path()[1:], path()))
    for node in network.widget.graph.nodes:
        node.classes = "path" if node.data["id"] in p else ""
    for edge in network.widget.graph.edges:
        key = (edge.data["source"], edge.data["target"])
        edge.classes = "path" if key in on_path_edges else ""
