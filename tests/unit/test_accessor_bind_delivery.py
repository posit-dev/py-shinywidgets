"""
Accessors attach while their output is still rendering, i.e. before the
widget's comm has opened. Whatever an attach sends the browser must still
arrive, after the widget's comm_open.
"""

from __future__ import annotations

from typing import Any, Callable

import plotly.graph_objects as go
import shinywidgets._bokeh_accessors as sb
import shinywidgets._plotly as sp
import shinywidgets._reactable as sr
from bokeh.plotting import figure
from ipywidgets import HTML
from jupyter_bokeh import BokehModel
from shiny import Session
from shiny.session import session_context
from shinywidgets._comm import OrphanedShinyComm

FlushToBrowser = Callable[[], list[dict[str, Any]]]


def custom_messages_after_open(
    msgs: list[dict[str, Any]], model_id: str
) -> list[dict[str, Any]]:
    """The custom messages `model_id` was sent, having checked they follow its open."""
    own = [m for m in msgs if m["content"]["comm_id"] == model_id]
    assert own[0]["type"] == "shinywidgets_comm_open"
    assert all(m["type"] == "shinywidgets_comm_msg" for m in own[1:])
    return [m["content"]["data"]["content"] for m in own[1:]]


def test_plotly_bind_sent_while_rendering_is_delivered(
    widget_session: Session, flush_to_browser: FlushToBrowser
) -> None:
    with session_context(widget_session):
        w = go.FigureWidget()
        assert isinstance(w.comm, OrphanedShinyComm)
        sp.CLICKED.attach(w, lambda raw: None)

    assert custom_messages_after_open(flush_to_browser(), w.model_id) == [
        {
            "shinywidgets": "bind",
            "events": ["plotly_click", "plotly_doubleclick", "plotly_deselect"],
        }
    ]


def test_reactable_bind_sent_while_rendering_is_delivered(
    widget_session: Session, flush_to_browser: FlushToBrowser
) -> None:
    with session_context(widget_session):
        # The bridge only needs a widget's on_msg()/send()
        w = HTML()
        assert isinstance(w.comm, OrphanedShinyComm)
        sr.SELECTED.attach(w, lambda raw: None)

    assert custom_messages_after_open(flush_to_browser(), w.model_id) == [
        sr.BIND_MESSAGE
    ]


def test_bokeh_event_subscription_made_while_rendering_is_delivered(
    widget_session: Session, flush_to_browser: FlushToBrowser
) -> None:
    p = figure()
    p.scatter([1, 2, 3], [4, 5, 6])
    with session_context(widget_session):
        w = BokehModel(p)
        assert isinstance(w.comm, OrphanedShinyComm)
        sb.TAPPED.attach(w, lambda raw: None)

    # Subscribing the plot to the event patches the browser's document
    patches = custom_messages_after_open(flush_to_browser(), w.model_id)
    assert patches and all(m["msg"] == "patch" for m in patches)
    assert any("subscribed_events" in m.get("payload", "") for m in patches)
