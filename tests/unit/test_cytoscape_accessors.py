from __future__ import annotations

from typing import Any, List

import networkx as nx
import shinywidgets._cytoscape as sc
import shinywidgets._render_widget as rw
from ipycytoscape import CytoscapeWidget, Node
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


def test_selected_specs_are_debounced_state() -> None:
    # Selection is state the widget always has (unlike clicks), and a
    # box-select changes many children's `selected` at once, so the default
    # is debounced. Lazy attach is fine for state: the attach seeds from the
    # children's current `selected` traits whenever it runs
    for spec in (sc.SELECTED_NODES, sc.SELECTED_EDGES):
        assert spec.kind == "state"
        assert spec.rate_policy == "debounce"


def test_selected_nodes_attach_seeds_and_observes(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    emitted: List[Any] = []
    detach = sc.SELECTED_NODES.attach(widget, emitted.append)
    # A state accessor seeds the current (empty) selection at attach
    assert emitted == [[]]
    widget.graph.nodes[0].selected = True
    assert [d["id"] for d in emitted[-1]] == ["a"]
    widget.graph.nodes[1].selected = True
    assert [d["id"] for d in emitted[-1]] == ["a", "b"]
    widget.graph.nodes[0].selected = False
    assert [d["id"] for d in emitted[-1]] == ["b"]
    detach()
    widget.graph.nodes[1].selected = False
    assert [d["id"] for d in emitted[-1]] == ["b"]  # no emits after detach


def test_selected_edges_attach_observes_edges_only(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    emitted: List[Any] = []
    detach = sc.SELECTED_EDGES.attach(widget, emitted.append)
    assert emitted == [[]]
    widget.graph.edges[0].selected = True
    assert len(emitted[-1]) == 1
    assert (emitted[-1][0]["source"], emitted[-1][0]["target"]) == ("a", "b")
    # A node selection doesn't reach the edge accessor
    widget.graph.nodes[0].selected = True
    assert len(emitted) == 2
    detach()


def test_selected_nodes_ignores_children_added_after_attach(
    widget_session: Session,
) -> None:
    # The documented limitation: children added to the graph after a render
    # aren't observed until the next render (re-attach)
    widget = make_widget(widget_session)
    emitted: List[object] = []
    detach = sc.SELECTED_NODES.attach(widget, emitted.append)
    with session_context(widget_session):
        widget.graph.add_node(Node(data={"id": "d"}))
    widget.graph.nodes[-1].selected = True
    assert emitted == [[]]
    detach()


def test_renderer_selected_round_trips_and_keeps_state(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    # rate_delay=0 turns the specs' debounce default off, for synchronous reads
    r = rw.render_ipycytoscape(rate_delay=0)
    r._widget = widget  # stands in for _render()
    r._accessors.on_render(widget)
    assert r.selected_nodes() == []
    assert r.selected_edges() == []
    widget.graph.nodes[0].selected = True
    assert [d["id"] for d in r.selected_nodes()] == ["a"]
    widget.graph.edges[0].selected = True
    assert len(r.selected_edges()) == 1
    assert [d["id"] for d in r.selected_nodes()] == ["a"]
    widget.graph.nodes[0].selected = False
    assert r.selected_nodes() == []
    # State semantics: a re-render doesn't reset the accessor...
    r._accessors.on_render(widget)
    assert len(r.selected_edges()) == 1
    # ...and the eager re-attach still reports changes
    widget.graph.edges[0].selected = False
    assert r.selected_edges() == []
