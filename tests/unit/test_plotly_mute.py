from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Sequence

import plotly.graph_objects as go
import pytest
import shinywidgets._plotly as sp
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_plotly, render_widget

from tests.unit.test_plotly_accessors import FakeFigureWidget

MUTE = {"shinywidgets": "mute", "traits": ["_js2py_pointsCallback"]}

Flush = Callable[[], List[Dict[str, Any]]]


def figure() -> go.FigureWidget:
    return go.FigureWidget(go.Scatter(x=[1, 2, 3], y=[1, 2, 3]))


def noop(*args: object) -> None:
    pass


def test_points_callback_trait_is_muted_without_native_callbacks(
    widget_session: Session,
) -> None:
    # plotly.py's widget syncs every click, hover and selection to Python
    # through this trait, per point, whether or not anything listens (#479)
    with session_context(widget_session):
        assert sp.muted_traits(figure()) == ["_js2py_pointsCallback"]


@pytest.mark.parametrize(
    "register",
    ["on_click", "on_hover", "on_unhover", "on_selection", "on_deselect"],
)
def test_native_callback_keeps_the_points_callback_trait(
    widget_session: Session, register: str
) -> None:
    with session_context(widget_session):
        fig = figure()
        getattr(fig.data[0], register)(noop)
        assert sp.muted_traits(fig) == []


def test_native_callback_on_any_trace_keeps_the_trait(widget_session: Session) -> None:
    with session_context(widget_session):
        fig = figure()
        fig.add_scatter(x=[1], y=[1])
        fig.data[1].on_click(noop)
        assert sp.muted_traits(fig) == []


def mute_requests(
    widget_session: Session,
    flush: Flush,
    build: Callable[[], go.FigureWidget],
    listen_to: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    """The mute requests the browser receives when `build()`'s figure renders."""
    r = render_plotly(listen_to=listen_to)

    @r
    def _() -> go.FigureWidget:
        return build()

    with session_context(widget_session):
        asyncio.get_event_loop().run_until_complete(r._render())
    custom = [
        m["content"]["data"]["content"]
        for m in flush()
        if m["type"] == "shinywidgets_comm_msg"
        and m["content"]["data"].get("method") == "custom"
    ]
    return [c for c in custom if c.get("shinywidgets") == "mute"]


def test_render_asks_the_browser_to_mute(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    assert mute_requests(widget_session, flush_to_browser, figure) == [MUTE]


def test_render_with_native_callback_mutes_nothing(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    def build() -> go.FigureWidget:
        fig = figure()
        fig.data[0].on_selection(noop)
        return fig

    assert mute_requests(widget_session, flush_to_browser, build) == []


def test_listening_to_native_mutes_nothing(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    # For what a render can't see: callbacks registered later, and reads of
    # plotly.py's Python-side `selectedpoints`
    requests = mute_requests(
        widget_session, flush_to_browser, figure, listen_to=["native"]
    )
    assert requests == []


def test_native_is_listened_to_alongside_accessors() -> None:
    r = render_plotly(listen_to=["native", "selected"])
    r._accessors.on_render(FakeFigureWidget())
    assert r.selected() is None


def test_misspelled_native_is_rejected_and_names_it() -> None:
    with pytest.raises(ValueError, match="'native'"):
        render_plotly(listen_to=["nativ"])


def test_native_is_not_a_name_for_renderers_that_mute_nothing() -> None:
    with pytest.raises(ValueError, match="native"):
        render_widget(listen_to=["native"])
