import networkx as nx
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipycytoscape

karate = nx.karate_club_graph()
LAYOUTS = ["cola", "circle", "concentric", "grid"]

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("layout", "Layout", LAYOUTS),
        ui.p("Click a member to see their connections.", class_="text-muted small"),
        ui.output_text_verbatim("selected"),
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
        return karate

    @reactive.effect
    def _():
        widget = network.widget
        widget.set_style(
            [
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
            ]
        )
        widget.on("node", "click", lambda node: clicked.set(int(node["data"]["id"])))

    @reactive.effect
    def _():
        # Change the layout in place, without re-rendering the graph
        network.widget.set_layout(name=input.layout())

    @render.text
    def selected():
        member = clicked.get()
        if member is None:
            return "No member selected"
        friends = sorted(karate.neighbors(member))
        club = karate.nodes[member]["club"]
        return f"Member {member} ({club})\nConnected to {len(friends)}: {friends}"


app = App(app_ui, server)
