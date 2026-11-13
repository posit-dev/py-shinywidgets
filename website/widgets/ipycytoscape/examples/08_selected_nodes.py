import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny.express import render, ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
STYLE = [{"selector": "node:selected", "style": {"background-color": "#e15759"}}]

ui.page_opts(title="selected_nodes()", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Click a node, or shift-drag a box to select a group")

        @render_ipycytoscape
        def network():
            widget = CytoscapeWidget(
                G, auto_unselectify=False, box_selection_enabled=True
            )
            widget.set_style(STYLE)
            widget.set_layout(name="cose")
            for node in widget.graph.nodes:
                node.selectable = True  # ipycytoscape defaults nodes to unselectable
            return widget

    with ui.card():
        ui.card_header("Group stats")

        @render.ui
        def stats():
            selected = {d["id"] for d in network.selected_nodes()}
            if not selected:
                return ui.p("Nothing selected.")
            sub = G.subgraph(selected)
            return ui.p(
                f"{len(selected)} characters, {sub.number_of_edges()} ties inside "
                f"the group, density {nx.density(sub):.2f}"
            )
