import io

import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny.express import render, ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
STYLE = [{"selector": "node:selected", "style": {"background-color": "#e15759"}}]

ui.page_opts(title="Read on demand", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Select a group, then export it -- no need to display it first")

        @render_ipycytoscape
        def network():
            widget = CytoscapeWidget(
                G, auto_unselectify=False, box_selection_enabled=True
            )
            widget.set_style(STYLE)
            widget.set_layout(name="cose")
            for node in widget.graph.nodes:
                node.selectable = True
            return widget

    with ui.card():
        ui.card_header("Export")
        ui.p("Nothing on this page reads selected_nodes() until you click Download.")

        @render.download_button(
            filename="selection.csv", label="Download selected characters"
        )
        def export():
            # Read on demand: no warm-up, no earlier display of this value --
            # selected_nodes() already has the latest selection the moment
            # the handler runs.
            rows = ["id"] + [d["id"] for d in network.selected_nodes()]
            yield io.BytesIO("\n".join(rows).encode()).getvalue()
