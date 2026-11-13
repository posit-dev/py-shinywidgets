import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny.express import render, ui
from shinywidgets import render_ipycytoscape

G = nx.karate_club_graph()

ui.page_opts(title="clicked_node()", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_ipycytoscape
        def network():
            widget = CytoscapeWidget(G)
            widget.set_layout(name="concentric")
            return widget

    with ui.card():
        ui.card_header("Clicked member")

        @render.ui
        def detail():
            clicked = network.clicked_node()
            if clicked is None:
                return ui.p("Click a member to see their connections.")
            member = int(clicked["data"]["id"])
            friends = sorted(G.neighbors(member))
            return ui.TagList(
                ui.h5(f"Member {member}"),
                ui.p(f"{G.nodes[member]['club']}'s faction"),
                ui.p(f"Connected to {len(friends)}: {', '.join(map(str, friends))}"),
            )
