from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterator

import ipycytoscape
import networkx as nx
import pytest
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny import Session
from shiny.session import session_context


@pytest.fixture(autouse=True)
def in_session(widget_session: Session) -> Iterator[None]:
    with session_context(widget_session):
        yield


def make_graph() -> nx.Graph:
    g = nx.Graph()
    g.add_edges_from([("a", "b"), ("b", "c")])
    return g


def test_networkx_graph_is_coerced_to_cytoscape_widget() -> None:
    res = rw.render_ipycytoscape()._as_widget(make_graph())
    assert isinstance(res, ipycytoscape.CytoscapeWidget)
    assert {n.data["id"] for n in res.graph.nodes} == {"a", "b", "c"}
    assert len(res.graph.edges) == 2


def test_directed_networkx_graph_is_coerced() -> None:
    g = nx.DiGraph([("a", "b")])
    res = rw.render_ipycytoscape()._as_widget(g)
    assert isinstance(res, ipycytoscape.CytoscapeWidget)
    assert len(res.graph.edges) == 1


def test_cytoscape_widget_passes_through_unchanged() -> None:
    w = ipycytoscape.CytoscapeWidget()
    assert rw.render_ipycytoscape()._as_widget(w) is w


def test_unsupported_value_raises_type_error() -> None:
    class NotAGraph: ...

    with pytest.raises(TypeError, match="coerce"):
        rw.render_ipycytoscape()._as_widget(NotAGraph())


def test_missing_ipycytoscape_gives_install_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "ipycytoscape", None)
    with pytest.raises(ImportError, match="pip install ipycytoscape"):
        rw.render_ipycytoscape()._as_widget(make_graph())


def test_render_exposes_cytoscape_widget() -> None:
    r = rw.render_ipycytoscape()

    @r
    def _():  # noqa: ANN202
        return make_graph()

    res = asyncio.run(r._render())

    assert res is not None
    assert isinstance(r.widget, ipycytoscape.CytoscapeWidget)
    assert res["widget_pkg"] == "ipycytoscape"


def test_layout_defaults_fill_by_default() -> None:
    _, fill = rwb.set_layout_defaults(ipycytoscape.CytoscapeWidget())
    assert fill is True


def test_explicit_widget_height_disables_fill() -> None:
    w = ipycytoscape.CytoscapeWidget()
    w.layout.height = "300px"
    _, fill = rwb.set_layout_defaults(w)
    assert fill is False
