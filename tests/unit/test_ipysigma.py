from __future__ import annotations

import asyncio
import sys
from typing import Any

import networkx as nx
import pytest
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from ipysigma import Sigma
from shiny import Session
from shiny.session import session_context


def test_render_ipysigma_coerces_networkx_graph(widget_session: Session) -> None:
    r = rw.render_ipysigma()

    @r
    def _():  # noqa: ANN202
        return nx.karate_club_graph()

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert isinstance(r.widget, Sigma)
    assert len(r.widget.data["nodes"]) == 34
    assert res["widget_pkg"] == "ipysigma"


def test_render_ipysigma_passes_through_sigma_widget(widget_session: Session) -> None:
    r = rw.render_ipysigma()

    with session_context(widget_session):
        sigma = Sigma(nx.path_graph(3))

        @r
        def _():  # noqa: ANN202
            return sigma

        asyncio.run(r._render())

    assert r.widget is sigma


def test_render_ipysigma_requires_ipysigma_package(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "ipysigma", None)
    r = rw.render_ipysigma()

    @r
    def _():  # noqa: ANN202
        return nx.path_graph(3)

    with session_context(widget_session):
        with pytest.raises(
            ImportError, match=r"pip install 'shinywidgets\[ipysigma\]'"
        ):
            asyncio.run(r._render())


def test_render_ipysigma_rejects_non_graph(widget_session: Session) -> None:
    r = rw.render_ipysigma()

    @r
    def _():  # noqa: ANN202
        return "not a graph"

    with session_context(widget_session):
        with pytest.raises(TypeError, match="graph"):
            asyncio.run(r._render())


def test_default_height_fills(widget_session: Session) -> None:
    with session_context(widget_session):
        sigma = Sigma(nx.path_graph(3))
        _, fill = rwb.set_layout_defaults(sigma)

    assert fill is True
    assert sigma.height == "100%"


@pytest.mark.parametrize(
    "kwargs, expected_height",
    [({"height": 300}, "300px"), ({"raw_height": "40vh"}, "40vh")],
)
def test_explicit_height_is_respected(
    widget_session: Session, kwargs: dict[str, Any], expected_height: str
) -> None:
    with session_context(widget_session):
        sigma = Sigma(nx.path_graph(3), **kwargs)
        _, fill = rwb.set_layout_defaults(sigma)

    assert fill is False
    assert sigma.height == expected_height


def test_explicit_percent_height_fills(widget_session: Session) -> None:
    with session_context(widget_session):
        sigma = Sigma(nx.path_graph(3), raw_height="100%")
        _, fill = rwb.set_layout_defaults(sigma)

    assert fill is True
    assert sigma.height == "100%"
