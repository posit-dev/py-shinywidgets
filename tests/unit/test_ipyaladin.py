from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip(
    "ipyaladin",
    reason="ipyaladin isn't installed (e.g., it lacks wheels for this Python version)",
)

from ipyaladin import Aladin
from ipywidgets import Layout
from shiny import Session
from shiny.session import session_context
from shinywidgets._render_widget_base import set_layout_defaults


def aladin(session: Session, **kwargs: Any) -> Aladin:
    with session_context(session):
        w = Aladin(**kwargs)
        # The default Layout() is constructed lazily, on first access
        w.layout  # noqa: B018
        return w


def test_default_height_fills(widget_session: Session) -> None:
    _, fill = set_layout_defaults(aladin(widget_session))
    assert fill is True


def test_explicit_widget_height_disables_fill(widget_session: Session) -> None:
    w = aladin(widget_session, height=300)
    _, fill = set_layout_defaults(w)
    assert fill is False
    # The container is sized to the widget's height so CSS can size the
    # aladin-lite viewer to it (its own inline height always matches _height)
    assert w.layout.height == "300px"


def test_layout_height_disables_fill(widget_session: Session) -> None:
    with session_context(widget_session):
        w = aladin(widget_session, layout=Layout(height="250px"))
    _, fill = set_layout_defaults(w)
    assert fill is False
