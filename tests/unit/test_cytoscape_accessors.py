from __future__ import annotations

from typing import List

import networkx as nx
import shinywidgets._cytoscape as sc
import shinywidgets._render_widget as rw
from ipycytoscape import CytoscapeWidget
from shiny import Session
from shiny.session import session_context


def make_widget(session: Session) -> CytoscapeWidget:
    with session_context(session):
        widget = CytoscapeWidget()
        graph = nx.Graph()
        graph.add_edges_from([("a", "b"), ("b", "c")])
        widget.graph.add_graph_from_networkx(graph)
    return widget


def test_node_clicked_spec_is_eager() -> None:
    # ipycytoscape's frontend drops click registrations made after the view
    # exists, so attach must happen in _render(), not on first read
    assert sc.NODE_CLICKED.eager and sc.EDGE_CLICKED.eager


def test_node_clicked_emits_element_json(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    emitted: List[object] = []
    detach = sc.NODE_CLICKED.attach(widget, emitted.append)
    detach_edge = sc.EDGE_CLICKED.attach(widget, lambda raw: None)
    # What the frontend sends: the clicked element's ele.json()
    widget._interaction_handlers["node"]["click"]({"data": {"id": "a"}})
    assert emitted == [{"data": {"id": "a"}}]
    # An edge click doesn't reach the node accessor
    widget._interaction_handlers["edge"]["click"]({"data": {"id": "ab"}})
    assert emitted == [{"data": {"id": "a"}}]
    detach()
    detach_edge()


def test_node_clicked_detach_unregisters(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    detach = sc.NODE_CLICKED.attach(widget, lambda raw: None)
    detach()
    assert not widget._interaction_handlers["node"]["click"].callbacks


def test_renderer_node_clicked_round_trips_and_resets(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    r = rw.render_ipycytoscape()
    r._widget = widget  # stands in for _render()
    r._accessors.on_render(widget)
    assert r.node_clicked() is None
    widget._interaction_handlers["node"]["click"]({"data": {"id": "a"}})
    assert r.node_clicked() == {"data": {"id": "a"}}
    # Event semantics: a re-render resets the accessor to None
    r._accessors.on_render(widget)
    assert r.node_clicked() is None
    # ...and the eager re-attach still reports clicks
    widget._interaction_handlers["node"]["click"]({"data": {"id": "b"}})
    assert r.node_clicked() == {"data": {"id": "b"}}
