import ipycytoscape
import networkx as nx
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipycytoscape

karate = nx.karate_club_graph()
LAYOUTS = ["cola", "circle", "concentric", "grid"]

STYLE = [
    {
        "selector": "node",
        "style": {"label": "data(id)", "font-size": "10px"},
    },
    {
        "selector": 'node[club = "Mr. Hi"]',
        "style": {"background-color": "#447099"},
    },
    {
        "selector": 'node[club = "Officer"]',
        "style": {"background-color": "#ee6331"},
    },
    {"selector": "edge", "style": {"width": 1}},
    {
        "selector": "node.clicked",
        "style": {"border-width": 3, "border-color": "#212529"},
    },
]

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("layout", "Layout", LAYOUTS),
        ui.p("Click a member to see their connections.", class_="text-muted small"),
        ui.output_ui("selected"),
    ),
    ui.card(
        ui.card_header("Zachary's karate club"),
        output_widget("network"),
        full_screen=True,
    ),
    title="ipycytoscape",
    fillable=True,
)


def server(input, output, session):
    clicked = reactive.value(None)

    @render_ipycytoscape
    def network():
        widget = ipycytoscape.CytoscapeWidget(karate)
        widget.set_style(STYLE)
        # Register callbacks here, before the graph is displayed: ipycytoscape
        # drops some callbacks registered later (e.g. from an effect)
        widget.on("node", "click", lambda node: clicked.set(int(node["data"]["id"])))
        return widget

    @reactive.effect
    def _():
        # Change the layout in place, without re-rendering the graph
        network.widget.set_layout(name=input.layout())

    @reactive.effect
    def _():
        # Highlight the clicked member in place, too
        member = clicked.get()
        for node in network.widget.graph.nodes:
            node.classes = "clicked" if node.data["id"] == str(member) else ""

    @render.ui
    def selected():
        member = clicked.get()
        if member is None:
            return ui.p("No member selected")
        friends = sorted(karate.neighbors(member))
        club = karate.nodes[member]["club"]
        return ui.TagList(
            ui.p(ui.strong(f"Member {member}"), f" ({club})"),
            ui.p(f"Connected to {len(friends)}: {', '.join(map(str, friends))}"),
        )


app = App(app_ui, server)
