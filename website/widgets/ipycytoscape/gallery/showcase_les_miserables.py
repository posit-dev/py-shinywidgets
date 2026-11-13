# Assigning to __doc__ (rather than a bare string literal) keeps this header
# out of the rendered page: shiny.express displays every top-level expression
# statement's value, docstrings included.
__doc__ = """
Les Miserables network (showcase)

networkx computes communities, degree and shortest paths on the classic
Les Miserables co-appearance graph; Cytoscape draws and restyles it live.
Click a character to see their circle, shift-drag a box to select a group,
click a tie for its scene count, or pick two characters for the path
between them. Everything restyles in place -- the graph never redraws.

Run: shiny run showcase_les_miserables.py
Data: networkx.les_miserables_graph() (bundled with networkx).
"""

import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
DEGREE: dict[str, int] = dict(G.degree())
# Strong ties (many shared scenes) are short hops for the shortest-path finder
nx.set_edge_attributes(
    G, {(u, v): 1 / d["weight"] for u, v, d in G.edges(data=True)}, "dist"
)
PALETTE = ["#4e79a7", "#e15759", "#59a14f", "#b07aa1", "#f28e2b", "#76b7b2"]
COMMUNITIES = sorted(
    nx.community.louvain_communities(G, weight="weight", seed=3), key=len, reverse=True
)
COMMUNITY = {n: i for i, c in enumerate(COMMUNITIES) for n in c}
# Name each community after its best-connected character
CIRCLE = [max(c, key=lambda n: DEGREE[n]) for c in COMMUNITIES]
LAYOUTS = {
    "cose": "Force-directed",
    "concentric": "Concentric (by degree)",
    "circle": "Circle",
}
CHARACTERS = sorted(G.nodes)

STYLE = [
    {
        "selector": "node",
        "style": {
            "background-color": "data(color)",
            "font-size": "mapData(degree, 1, 36, 8, 15)",
            "color": "#333",
            "min-zoomed-font-size": 6,
            "width": "mapData(degree, 1, 36, 12, 54)",
            "height": "mapData(degree, 1, 36, 12, 54)",
            "text-outline-color": "#fff",
            "text-outline-width": 2,
        },
    },
    {
        "selector": "edge",
        "style": {
            "width": "mapData(weight, 1, 31, 0.6, 9)",
            "line-color": "#c9ced6",
            "curve-style": "haystack",
            "opacity": 0.8,
        },
    },
    {
        "selector": "node[degree >= 10], node.focus, node.path",
        "style": {"label": "data(id)"},
    },
    {"selector": ".faded", "style": {"opacity": 0.12, "text-opacity": 0}},
    {"selector": "node:selected", "style": {"border-width": 3, "border-color": "#222"}},
    {"selector": "edge.focus", "style": {"line-color": "#7a8290", "opacity": 1}},
    {
        "selector": "node.path",
        "style": {"border-width": 4, "border-color": "#111", "font-weight": "bold"},
    },
    {
        "selector": "edge.path",
        "style": {"line-color": "#111", "width": 5, "opacity": 1},
    },
]

ui.page_opts(title="Les Misérables network", fillable=True)
with ui.sidebar(width=320):
    ui.input_select("layout", "Layout", LAYOUTS)
    ui.input_selectize(
        "path",
        "Shortest path between",
        CHARACTERS,
        multiple=True,
        options={"maxItems": 2, "placeholder": "Pick two characters"},
    )

    @render.ui
    def legend():
        return ui.div(
            *[
                ui.div(
                    ui.span(
                        style=(
                            "display:inline-block;width:.75em;height:.75em;"
                            f"border-radius:50%;background:{PALETTE[i]}"
                        )
                    ),
                    f" {name}'s circle",
                    class_="small",
                )
                for i, name in enumerate(CIRCLE)
            ]
        )

    @render.ui
    def info():
        p = path()
        lines = [ui.p(ui.strong("Path: "), " → ".join(p), class_="small")] if p else []
        clicked = network.clicked_node()
        tie = network.clicked_edge()
        if clicked is not None:
            name = clicked["data"]["id"]
            top = sorted(G[name].items(), key=lambda kv: -kv[1]["weight"])[:5]
            lines += [
                ui.h5(name),
                ui.p(
                    f"{DEGREE[name]} co-characters · {CIRCLE[COMMUNITY[name]]}'s circle",
                    class_="small",
                ),
                ui.tags.ul(
                    *[ui.tags.li(f"{m} ({d['weight']} scenes)") for m, d in top],
                    class_="small",
                ),
            ]
        if tie is not None:
            d = tie["data"]
            lines += [
                ui.p(
                    f"{d['source']} + {d['target']}: {d['weight']} scenes",
                    class_="small",
                )
            ]
        return (
            ui.div(*lines)
            if lines
            else ui.p("Click a character or tie.", class_="text-muted")
        )


with ui.card(full_screen=True):
    ui.card_header("Click a character · shift-drag to select a group · click a tie")

    @render_ipycytoscape
    def network():
        w = CytoscapeWidget(G, auto_unselectify=False, box_selection_enabled=True)
        w.set_style(STYLE)
        for n in w.graph.nodes:
            name = n.data["id"]
            n.data = {
                **n.data,
                "degree": DEGREE[name],
                "color": PALETTE[COMMUNITY[name]],
            }
            n.selectable = True  # ipycytoscape defaults to unselectable nodes
        with reactive.isolate():
            w.set_layout(name=input.layout(), nodeRepulsion=40000, idealEdgeLength=70)
        return w

    @reactive.effect
    def _():
        network.widget.set_layout(name=input.layout(), animate=False)

    @render.ui
    def group_stats():
        sel = {d["id"] for d in network.selected_nodes()}
        if len(sel) < 2:
            return None
        sub = G.subgraph(sel)
        return ui.div(
            f"{len(sel)} characters · {sub.number_of_edges()} ties inside the group · "
            f"density {nx.density(sub):.2f}",
            class_="small text-muted position-absolute top-0 end-0 m-2 bg-white p-1 border rounded",
        )

    @reactive.effect
    def _():
        # Restyle in place by toggling element classes: no re-render, the
        # layout never reruns and the user's pan/zoom survives
        clicked = network.clicked_node()
        center = clicked["data"]["id"] if clicked else None
        p = path()
        focus = {center, *G[center]} if center else set()
        on_path_edges = set(zip(p, p[1:])) | set(zip(p[1:], p))
        lit = focus | set(p)
        for n in network.widget.graph.nodes:
            nid = n.data["id"]
            n.classes = " ".join(
                c
                for c, on in [
                    ("faded", bool(lit) and nid not in lit),
                    ("focus", nid == center),
                    ("path", nid in p),
                ]
                if on
            )
        for e in network.widget.graph.edges:
            s, t = e.data["source"], e.data["target"]
            in_focus = center in (s, t)
            e.classes = " ".join(
                c
                for c, on in [
                    ("faded", bool(lit) and not (in_focus or (s, t) in on_path_edges)),
                    ("focus", in_focus),
                    ("path", (s, t) in on_path_edges),
                ]
                if on
            )


@reactive.calc
def path() -> list[str]:
    ends = input.path()
    if len(ends) != 2:
        return []
    return nx.shortest_path(G, *ends, weight="dist")
