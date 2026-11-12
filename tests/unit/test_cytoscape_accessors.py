from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Dict, List, Tuple, cast

import networkx as nx
import shinywidgets._cytoscape as sc
import shinywidgets._render_widget as rw
from ipycytoscape import CytoscapeWidget, Node
from shiny import Session
from shiny.session import session_context
from shinywidgets._accessors import Accessors


def node_ids(raw: object) -> List[str]:
    data = cast(List[Dict[str, Any]], sc.SELECTED_NODES.payload(raw))
    return [d["id"] for d in data]


def edge_datas(raw: object) -> List[Dict[str, Any]]:
    return cast(List[Dict[str, Any]], sc.SELECTED_EDGES.payload(raw))


def make_widget(session: Session) -> CytoscapeWidget:
    with session_context(session):
        widget = CytoscapeWidget()
        graph = nx.Graph()
        graph.add_edges_from([("a", "b"), ("b", "c")])
        widget.graph.add_graph_from_networkx(graph)
    return widget


def test_clicked_node_attaches_at_render() -> None:
    # Like every accessor, the click specs attach at render, so a click
    # before the first read isn't lost
    assert sc.CLICKED_NODE.kind == "state" and sc.CLICKED_EDGE.kind == "state"


def test_clicked_node_emits_element_json(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    emitted: List[object] = []
    detach = sc.CLICKED_NODE.attach(widget, emitted.append)
    detach_edge = sc.CLICKED_EDGE.attach(widget, lambda raw: None)
    # What the frontend sends: the clicked element's ele.json()
    widget._interaction_handlers["node"]["click"]({"data": {"id": "a"}})
    assert emitted == [{"data": {"id": "a"}}]
    # An edge click doesn't reach the node accessor
    widget._interaction_handlers["edge"]["click"]({"data": {"id": "ab"}})
    assert emitted == [{"data": {"id": "a"}}]
    detach()
    detach_edge()


def test_clicked_node_detach_unregisters(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    detach = sc.CLICKED_NODE.attach(widget, lambda raw: None)
    detach()
    assert not widget._interaction_handlers["node"]["click"].callbacks


def test_renderer_clicked_node_round_trips_and_is_retained(
    widget_session: Session,
) -> None:
    widget = make_widget(widget_session)
    r = rw.render_ipycytoscape()
    r._widget = widget  # stands in for _render()
    r._accessors.on_render(widget)
    assert r.clicked_node() is None
    widget._interaction_handlers["node"]["click"]({"data": {"id": "a"}})
    assert r.clicked_node() == {"data": {"id": "a"}}
    # Retained semantics: a re-render keeps the last click (it still happened)
    r._accessors.on_render(widget)
    assert r.clicked_node() == {"data": {"id": "a"}}
    # ...and the re-attach still reports clicks
    widget._interaction_handlers["node"]["click"]({"data": {"id": "b"}})
    assert r.clicked_node() == {"data": {"id": "b"}}


def test_click_accessors_are_retained() -> None:
    assert sc.CLICKED_NODE.kind == "state"
    assert sc.CLICKED_EDGE.kind == "state"


def test_selected_specs_are_debounced_state() -> None:
    # Selection is state the widget always has (unlike clicks), and a
    # box-select changes many children's `selected` at once, so the default
    # is debounced
    for spec in (sc.SELECTED_NODES, sc.SELECTED_EDGES):
        assert spec.kind == "state"
        assert spec.rate_policy == "debounce"


def test_selected_nodes_attach_seeds_and_observes(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    emitted: List[Any] = []
    detach = sc.SELECTED_NODES.attach(widget, emitted.append)
    # A state accessor seeds the current (empty) selection at attach
    assert node_ids(emitted[0]) == []
    widget.graph.nodes[0].selected = True
    assert node_ids(emitted[-1]) == ["a"]
    widget.graph.nodes[1].selected = True
    assert node_ids(emitted[-1]) == ["a", "b"]
    widget.graph.nodes[0].selected = False
    assert node_ids(emitted[-1]) == ["b"]
    detach()
    widget.graph.nodes[1].selected = False
    assert node_ids(emitted[-1]) == ["b"]  # no emits after detach


def test_selected_edges_attach_observes_edges_only(widget_session: Session) -> None:
    widget = make_widget(widget_session)
    emitted: List[Any] = []
    detach = sc.SELECTED_EDGES.attach(widget, emitted.append)
    assert edge_datas(emitted[0]) == []
    widget.graph.edges[0].selected = True
    edge = edge_datas(emitted[-1])[0]
    assert (edge["source"], edge["target"]) == ("a", "b")
    # A node selection doesn't reach the edge accessor
    widget.graph.nodes[0].selected = True
    assert len(emitted) == 2
    detach()


def test_selected_nodes_republishes_without_removed_selected_child(
    widget_session: Session,
) -> None:
    widget = make_widget(widget_session)
    emitted: List[Any] = []
    detach = sc.SELECTED_NODES.attach(widget, emitted.append)
    node_a, node_b, _ = widget.graph.nodes
    node_a.selected = True
    widget.graph.remove_node(node_a)
    assert node_ids(emitted[-1]) == []
    # The removed child's `selected` observer was detached
    n = len(emitted)
    node_a.selected = False
    assert len(emitted) == n
    node_b.selected = True
    assert node_ids(emitted[-1]) == ["b"]
    detach()


def test_selected_edges_republishes_without_removed_selected_child(
    widget_session: Session,
) -> None:
    widget = make_widget(widget_session)
    r = rw.render_ipycytoscape(rate_delay=0)
    r._widget = widget  # stands in for _render()
    r._accessors.on_render(widget)
    edge = widget.graph.edges[0]
    edge.selected = True
    assert len(r.selected_edges()) == 1
    widget.graph.remove_edge(edge)
    assert r.selected_edges() == []


def test_selected_nodes_follow_graph_order_on_reorder(
    widget_session: Session,
) -> None:
    widget = make_widget(widget_session)
    r = rw.render_ipycytoscape(rate_delay=0)
    r._widget = widget  # stands in for _render()
    r._accessors.on_render(widget)
    widget.graph.nodes[0].selected = True
    widget.graph.nodes[2].selected = True
    assert [d["id"] for d in r.selected_nodes()] == ["a", "c"]
    widget.graph.nodes.reverse()
    assert [d["id"] for d in r.selected_nodes()] == ["c", "a"]


def test_selected_nodes_tracks_children_added_after_attach(
    widget_session: Session,
) -> None:
    widget = make_widget(widget_session)
    r = rw.render_ipycytoscape(rate_delay=0)
    r._widget = widget  # stands in for _render()
    r._accessors.on_render(widget)
    with session_context(widget_session):
        widget.graph.add_node(Node(data={"id": "d"}))
    widget.graph.nodes[-1].selected = True
    assert [d["id"] for d in r.selected_nodes()] == ["d"]


def test_selected_burst_emits_cheap_raws_and_materializes_once_per_publication(
    widget_session: Session,
) -> None:
    widget = make_widget(widget_session)
    raws: List[object] = []
    detach = sc.SELECTED_NODES.attach(widget, raws.append)
    # A box-select-shaped burst: each child toggles once
    for node in widget.graph.nodes:
        node.selected = True
    detach()
    # The attach emits one cheap raw per toggle (plus the seed): the graph
    # order and the selected set, not the user-facing data list
    assert len(raws) == 1 + len(widget.graph.nodes)
    for raw in raws:
        order, selected = cast(Tuple[object, object], raw)
        assert isinstance(order, tuple) and isinstance(selected, frozenset)

    # The data list is built by the spec's payload, which runs once per
    # publication (post-debounce), not per notification
    calls = 0

    def counting_payload(raw: Any) -> object:
        nonlocal calls
        calls += 1
        return sc.SELECTED_NODES.payload(raw)

    spec = replace(sc.SELECTED_NODES, payload=counting_payload)
    pending: List[Callable[[], None]] = []

    def schedule(delay: float, fn: Callable[[], None]) -> Callable[[], None]:
        cancelled = False

        def run() -> None:
            if not cancelled:
                fn()

        def cancel() -> None:
            nonlocal cancelled
            cancelled = True

        pending.append(run)
        return cancel

    accessors = Accessors([spec], schedule=schedule)
    accessors.on_render(widget)
    for node in widget.graph.nodes:
        node.selected = False
    assert calls == 0  # debounced: nothing published yet
    for fn in pending:
        fn()
    accessors.read("selected_nodes")
    accessors.read("selected_nodes")  # memoized per publication
    assert calls == 1


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
    # ...and the render-time re-attach still reports changes
    widget.graph.edges[0].selected = False
    assert r.selected_edges() == []
