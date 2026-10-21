import networkx as nx
from ipysigma import Sigma
from networkx.algorithms.community import greedy_modularity_communities
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipysigma

# Zachary's karate club: members are nodes, friendships outside the club are edges
G = nx.karate_club_graph()
for i, members in enumerate(greedy_modularity_communities(G)):
    for member in members:
        G.nodes[member]["community"] = i

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_radio_buttons(
            "size",
            "Size nodes by",
            {"degree": "Number of friends", "betweenness": "Betweenness"},
        ),
        ui.p(
            "Click a node (or use the search box inside the graph) and the sidebar "
            "shows who it's connected to. Drag the graph to pan, scroll to zoom, "
            "and press play to run a force-directed layout.",
            class_="text-muted small",
        ),
        ui.output_ui("details"),
    ),
    ui.card(
        ui.card_header("Karate club"),
        output_widget("graph"),
        full_screen=True,
    ),
    title="ipysigma",
)


def server(input, output, session):
    @render_ipysigma
    def graph():
        # Changing the sizing re-renders the graph; start_layout=True lays it out
        # automatically, and the explicit Sigma gives access to all its options
        size = (
            dict(G.degree)
            if input.size() == "degree"
            else nx.betweenness_centrality(G)
        )
        return Sigma(
            G,
            node_size=size,
            node_color="community",
            node_label="club",
            start_layout=True,
        )

    @reactive.calc
    def selected_node() -> int | None:
        node = reactive_read(graph.widget, "selected_node")
        return None if node is None else int(node)

    @render.ui
    def details():
        node = selected_node()
        if node is None:
            return ui.p("No node selected.")
        friends = sorted(G.neighbors(node))
        return ui.TagList(
            ui.h5(f"Member {node}"),
            ui.p(f"Club: {G.nodes[node]['club']}"),
            ui.p(f"Friends ({len(friends)}): {', '.join(map(str, friends))}"),
        )


app = App(app_ui, server)
