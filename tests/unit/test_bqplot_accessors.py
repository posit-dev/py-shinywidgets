from __future__ import annotations

from typing import Any, Tuple

import numpy as np
import pandas as pd
import shinywidgets._bqplot as sb
from shiny import Session
from shiny.session import session_context

DF = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [4.0, 5.0, 6.0], "c": list("abc")})


def figure(session: Session) -> Tuple[Any, Any]:
    from bqplot import Figure, Scatter
    from bqplot.interacts import BrushSelector

    with session_context(session):
        sc = Scatter(x=[1, 2, 3], y=[4, 5, 6])
        return Figure(marks=[sc], interaction=BrushSelector()), sc


def test_selected_seeds_per_mark_state(widget_session: Session) -> None:
    fig, sc = figure(widget_session)
    emitted: list[object] = []
    detach = sb.SELECTED.attach(fig, emitted.append)
    assert emitted == [[None]]  # one entry per mark; None until that mark is selected
    sc.selected = np.array([0, 2], dtype=np.uint32)
    assert [list(s) for s in emitted[-1]] == [[0, 2]]
    detach()


def test_selected_dedupes_equal_selections(widget_session: Session) -> None:
    # bqplot selectors re-send the same selection during a drag; the helper's
    # equality check can't compare arrays, so attach does its own
    fig, sc = figure(widget_session)
    emitted: list[object] = []
    sb.SELECTED.attach(fig, emitted.append)
    sc.selected = np.array([1], dtype=np.uint32)
    n = len(emitted)
    sc.selected = np.array([1], dtype=np.uint32)
    assert len(emitted) == n


def test_selected_reattaches_when_marks_change(widget_session: Session) -> None:
    from bqplot import Scatter

    fig, sc = figure(widget_session)
    emitted: list[object] = []
    detach = sb.SELECTED.attach(fig, emitted.append)
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


def test_brush_seeds_and_emits_the_region(widget_session: Session) -> None:
    fig, _ = figure(widget_session)
    emitted: list[object] = []
    detach = sb.BRUSH.attach(fig, emitted.append)
    assert emitted == [None]  # a fresh BrushSelector's selected is None
    fig.interaction.selected = np.array([[1.0, 3.0], [1.2, 4.0]])
    assert np.array_equal(emitted[-1], np.array([[1.0, 3.0], [1.2, 4.0]]))
    detach()


def test_brush_reattaches_and_resets_on_interaction_swap(
    widget_session: Session,
) -> None:
    from bqplot.interacts import BrushIntervalSelector, PanZoom

    fig, _ = figure(widget_session)
    emitted: list[object] = []
    detach = sb.BRUSH.attach(fig, emitted.append)
    fig.interaction.selected = np.array([[1.0, 3.0], [1.2, 4.0]])

    # Swapping the interaction (what the toolbar does) re-attaches; a
    # selector with no region trait (PanZoom) resets brush() to None
    with session_context(widget_session):
        fig.interaction = PanZoom()
    assert emitted[-1] is None

    # ... and a new selector seeds its own state
    with session_context(widget_session):
        sel = BrushIntervalSelector()
    sel.selected = np.array([1.0, 2.5])
    fig.interaction = sel
    assert np.array_equal(emitted[-1], np.array([1.0, 2.5]))
    sel.selected = np.array([2.0, 3.5])
    assert np.array_equal(emitted[-1], np.array([2.0, 3.5]))
    detach()


def test_brush_accessor(widget_session: Session) -> None:
    from shinywidgets import render_bqplot

    fig, _ = figure(widget_session)
    r = render_bqplot(rate_delay=0)
    r._widget = fig  # stands in for _render()
    r._accessors.on_render(fig)
    assert r.brush() is None
    fig.interaction.selected = np.array([[0.5, 2.5], [3.5, 5.5]])
    assert np.array_equal(r.brush(), np.array([[0.5, 2.5], [3.5, 5.5]]))


def test_selected_seeds_empty_for_a_figure_with_no_marks(
    widget_session: Session,
) -> None:
    from bqplot import Figure

    with session_context(widget_session):
        fig = Figure()
    emitted: list[object] = []
    detach = sb.SELECTED.attach(fig, emitted.append)
    # The seed must publish even though the empty selection list compares
    # equal to the dedup baseline
    assert emitted == [[]]
    detach()


def test_selected_publishes_empty_when_marks_are_removed(
    widget_session: Session,
) -> None:
    fig, sc = figure(widget_session)
    emitted: list[object] = []
    detach = sb.SELECTED.attach(fig, emitted.append)
    sc.selected = np.array([1], dtype=np.uint32)
    fig.marks = []
    assert emitted[-1] == []
    detach()


def test_selections_equal() -> None:
    assert sb.selections_equal([None], [None])
    assert sb.selections_equal([np.array([1])], [np.array([1])])
    assert not sb.selections_equal([np.array([1])], [np.array([2])])
    assert not sb.selections_equal([None], [np.array([1])])
    assert not sb.selections_equal([None], [None, None])


def test_selected_accessor(widget_session: Session) -> None:
    from shinywidgets import render_bqplot

    fig, sc = figure(widget_session)
    r = render_bqplot(rate_delay=0)  # undo the default debounce for the test
    r._widget = fig  # stands in for _render()
    r._accessors.on_render(fig)
    assert r.selected() == [None]
    sc.selected = np.array([2, 1], dtype=np.uint32)
    assert [list(s) for s in r.selected()] == [[2, 1]]


def bqplot_render(widget_session: Session, marks: int = 1) -> Tuple[Any, Any]:
    from bqplot import Figure, Scatter

    with session_context(widget_session):
        scatters = [Scatter(x=[1, 2, 3], y=[4, 5, 6]) for _ in range(marks)]
        fig = Figure(marks=scatters)
    from shinywidgets import render_bqplot

    r = render_bqplot(rate_delay=0)  # undo the default debounce for the test
    r._widget = fig  # stands in for _render()
    r._accessors.on_render(fig)
    return r, fig


def test_selected_rows_single_mark_no_selection_is_empty(
    widget_session: Session,
) -> None:
    r, _ = bqplot_render(widget_session)
    out = r.selected_rows(DF)
    assert isinstance(out, pd.DataFrame)
    assert len(out) == 0
    assert list(out.columns) == list(DF.columns)


def test_selected_rows_single_mark_default(widget_session: Session) -> None:
    r, fig = bqplot_render(widget_session)
    fig.marks[0].selected = np.array([2, 0], dtype=np.uint32)
    out = r.selected_rows(DF)
    assert isinstance(out, pd.DataFrame)
    assert out["c"].tolist() == ["c", "a"]  # selection order, not frame order


def test_selected_rows_explicit_frame_keeps_its_type(
    widget_session: Session,
) -> None:
    import polars as pl

    r, fig = bqplot_render(widget_session)
    fig.marks[0].selected = np.array([1], dtype=np.uint32)
    out = r.selected_rows(pl.DataFrame({"y": [4.0, 5.0, 6.0]}))
    assert isinstance(out, pl.DataFrame)
    assert out["y"].to_list() == [5.0]


def test_selected_rows_empty_selection_is_empty_frame(
    widget_session: Session,
) -> None:
    r, fig = bqplot_render(widget_session)
    fig.marks[0].selected = np.array([], dtype=np.uint32)
    out = r.selected_rows(DF)
    assert len(out) == 0
    assert list(out.columns) == list(DF.columns)


def test_selected_rows_multi_mark_requires_mark(widget_session: Session) -> None:
    import pytest

    r, _ = bqplot_render(widget_session, marks=2)
    with pytest.raises(ValueError, match="mark="):
        r.selected_rows(DF)


def test_selected_rows_mark_by_index(widget_session: Session) -> None:
    r, fig = bqplot_render(widget_session, marks=2)
    fig.marks[0].selected = np.array([0], dtype=np.uint32)
    fig.marks[1].selected = np.array([2, 1], dtype=np.uint32)
    out = r.selected_rows(DF, mark=1)
    assert out["c"].tolist() == ["c", "b"]


def test_selected_rows_mark_by_mark_object(widget_session: Session) -> None:
    r, fig = bqplot_render(widget_session, marks=2)
    fig.marks[1].selected = np.array([1], dtype=np.uint32)
    out = r.selected_rows(DF, mark=fig.marks[1])
    assert out["c"].tolist() == ["b"]


def test_selected_rows_mark_object_not_in_figure(widget_session: Session) -> None:
    import pytest
    from bqplot import Scatter

    r, _ = bqplot_render(widget_session, marks=2)
    with session_context(widget_session):
        other = Scatter(x=[1], y=[2])
    with pytest.raises(ValueError, match="not one of"):
        r.selected_rows(DF, mark=other)
