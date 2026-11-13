import networkx as nx
from shiny.express import ui
from shinywidgets import render_ipycytoscape

ui.page_opts(title="Zachary's karate club", fillable=True)

with ui.card(full_screen=True):

    @render_ipycytoscape
    def network():
        return nx.karate_club_graph()
