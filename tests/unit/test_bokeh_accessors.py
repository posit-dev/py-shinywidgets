from __future__ import annotations

from typing import Any, List, Tuple

import pandas as pd
import pytest
import shinywidgets._bokeh_accessors as sb
from bokeh.events import RangesUpdate, Tap
from bokeh.layouts import row
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from jupyter_bokeh import BokehModel
from shiny import Session
from shiny.session import session_context


def plot() -> Tuple[Any, ColumnDataSource]:
    src = ColumnDataSource({"x": [1, 2, 3], "y": [4, 5, 6]})
    p = figure()
    p.scatter("x", "y", source=src)
    return p, src


def widget(session: Session, model: Any) -> BokehModel:
    with session_context(session):
        return BokehModel(model)


def test_selected_emits_indices_once_per_change(widget_session: Session) -> None:
    p, src = plot()
    w = widget(widget_session, p)
    emitted: List[object] = []
    detach = sb.SELECTED.attach(w, emitted.append)
    assert emitted == []  # event-kind: nothing until a gesture
    src.selected.indices = [1, 2]
    assert emitted == [[1, 2]]
    detach()
    src.selected.indices = [0]
    assert emitted == [[1, 2]]


def test_selected_requires_a_single_source(widget_session: Session) -> None:
    (p1, _), (p2, _) = plot(), plot()
    w = widget(widget_session, row(p1, p2))
    with pytest.raises(TypeError, match="on_change"):
        sb.SELECTED.attach(w, lambda raw: None)


def test_tapped_subscribes_so_browser_events_arrive(widget_session: Session) -> None:
    p, _ = plot()
    w = widget(widget_session, p)
    emitted: List[object] = []
    detach = sb.TAPPED.attach(w, emitted.append)
    # What jupyter_bokeh does with a browser event: only subscribed models get it
    tap = Tap(model=p, x=1.5, y=4.5)
    p.document.callbacks.trigger_event(tap)
    assert emitted == [tap]
    detach()
    p.document.callbacks.trigger_event(Tap(model=p, x=0, y=0))
    assert emitted == [tap]


def test_zoomed_reports_ranges_update(widget_session: Session) -> None:
    p, _ = plot()
    w = widget(widget_session, p)
    emitted: List[object] = []
    sb.ZOOMED.attach(w, emitted.append)
    ev = RangesUpdate(model=p, x0=0, x1=1, y0=2, y1=3)
    p.document.callbacks.trigger_event(ev)
    assert emitted == [ev]


def test_selected_rows(widget_session: Session) -> None:
    from shinywidgets import render_bokeh

    p, src = plot()
    w = widget(widget_session, p)
    r = render_bokeh(rate_delay=0)
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    assert r.selected() is None
    out = r.selected_rows()
    assert isinstance(out, pd.DataFrame) and len(out) == 0
    src.selected.indices = [2, 0]
    assert r.selected() == [2, 0]
    assert r.selected_rows()["x"].tolist() == [3, 1]
