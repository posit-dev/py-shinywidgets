from __future__ import annotations

from typing import Any, Tuple

import numpy as np
import shinywidgets._bqplot as sb
from shiny import Session
from shiny.session import session_context


def figure(session: Session) -> Tuple[Any, Any]:
    from bqplot import Figure, Scatter
    from bqplot.interacts import BrushSelector

    with session_context(session):
        sc = Scatter(x=[1, 2, 3], y=[4, 5, 6])
        return Figure(marks=[sc], interaction=BrushSelector()), sc


def test_selection_seeds_per_mark_state(widget_session: Session) -> None:
    fig, sc = figure(widget_session)
    emitted: list[object] = []
    detach = sb.SELECTION.attach(fig, emitted.append)
    assert emitted == [[None]]  # one entry per mark; None until that mark is selected
    sc.selected = np.array([0, 2], dtype=np.uint32)
    assert [list(s) for s in emitted[-1]] == [[0, 2]]
    detach()


def test_selection_dedupes_equal_selections(widget_session: Session) -> None:
    # bqplot selectors re-send the same selection during a drag; the helper's
    # equality check can't compare arrays, so attach does its own
    fig, sc = figure(widget_session)
    emitted: list[object] = []
    sb.SELECTION.attach(fig, emitted.append)
    sc.selected = np.array([1], dtype=np.uint32)
    n = len(emitted)
    sc.selected = np.array([1], dtype=np.uint32)
    assert len(emitted) == n


def test_selection_reattaches_when_marks_change(widget_session: Session) -> None:
    from bqplot import Scatter

    fig, sc = figure(widget_session)
    emitted: list[object] = []
    detach = sb.SELECTION.attach(fig, emitted.append)
    sc.selected = np.array([1], dtype=np.uint32)

    with session_context(widget_session):
        new_mark = Scatter(x=[1, 2], y=[3, 4])
    fig.marks = [sc, new_mark]
    # Replacing marks publishes the new alignment: a kept mark's selection
    # carries over (it's the same mark object), and the new mark has none yet
    assert [None if s is None else list(s) for s in emitted[-1]] == [[1], None]
    new_mark.selected = np.array([0], dtype=np.uint32)
    assert [None if s is None else list(s) for s in emitted[-1]] == [[1], [0]]

    # A removed mark's observer must not linger (cached figures stack handlers)
    fig.marks = [new_mark]
    sc.selected = np.array([2], dtype=np.uint32)
    assert len(emitted[-1]) == 1
    detach()


def test_selections_equal() -> None:
    assert sb.selections_equal([None], [None])
    assert sb.selections_equal([np.array([1])], [np.array([1])])
    assert not sb.selections_equal([np.array([1])], [np.array([2])])
    assert not sb.selections_equal([None], [np.array([1])])
    assert not sb.selections_equal([None], [None, None])


def test_selection_accessor(widget_session: Session) -> None:
    from shinywidgets import render_bqplot

    fig, sc = figure(widget_session)
    r = render_bqplot(rate_delay=0)  # undo the default debounce for the test
    r._widget = fig  # stands in for _render()
    r._accessors.on_render(fig)
    assert r.selection() == [None]
    sc.selected = np.array([2, 1], dtype=np.uint32)
    assert [list(s) for s in r.selection()] == [[2, 1]]
