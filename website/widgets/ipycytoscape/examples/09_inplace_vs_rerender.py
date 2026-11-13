import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
STYLE = [
    {"selector": "node", "style": {"background-color": "#447099"}},
    {"selector": "node.highlight", "style": {"background-color": "#e15759"}},
]

ui.page_opts(title="In-place update vs. re-render", fillable=True)
ui.p("Scroll to zoom or drag to pan, then try each button.", class_="text-muted")
with ui.layout_columns(col_widths=[6, 6]):
    ui.input_action_button("highlight", "Highlight high-degree nodes (in place)")
    ui.input_action_button("rerender", "Re-render from scratch")

with ui.card(full_screen=True):

    @render_ipycytoscape
    def network():
        input.rerender()  # only this button forces a full rebuild
        widget = CytoscapeWidget(G)
        widget.set_style(STYLE)
        widget.set_layout(name="cose")
        return widget

    @reactive.effect
    @reactive.event(input.highlight)
    def _():
        # Toggles a class on each node: no re-render, no relayout, so the
        # user's current pan/zoom is untouched
        for node in network.widget.graph.nodes:
            node.classes = "highlight" if G.degree(node.data["id"]) >= 15 else ""
