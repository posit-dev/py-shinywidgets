import networkx as nx
import pandas as pd
from ipycytoscape import CytoscapeWidget
from shiny.express import ui
from shinywidgets import render_ipycytoscape

edges = pd.DataFrame(
    {
        "source": [
            "shinywidgets",
            "shinywidgets",
            "shiny",
            "shiny",
            "shiny",
            "pandas",
            "ipywidgets",
            "ipywidgets",
        ],
        "target": [
            "shiny",
            "ipywidgets",
            "starlette",
            "uvicorn",
            "htmltools",
            "numpy",
            "traitlets",
            "ipython",
        ],
    }
)
G = nx.from_pandas_edgelist(edges, create_using=nx.DiGraph)

STYLE = [
    {"selector": "node", "style": {"label": "data(id)", "background-color": "#447099"}},
    {
        "selector": "edge",
        "style": {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#9dbaea",
            "line-color": "#9dbaea",
        },
    },
]

ui.page_opts(title="A dependency graph from a pandas edge list", fillable=True)

with ui.card(full_screen=True):

    @render_ipycytoscape
    def network():
        widget = CytoscapeWidget(G)
        widget.set_style(STYLE)
        widget.set_layout(name="breadthfirst", directed=True, padding=20)
        return widget
