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
from shiny.reactive._core import Context
from shiny.session import session_context


def plot() -> Tuple[Any, ColumnDataSource]:
    src = ColumnDataSource({"x": [1, 2, 3], "y": [4, 5, 6]})
    p = figure()
    p.scatter("x", "y", source=src)
    return p, src


def widget(session: Session, model: Any) -> BokehModel:
    with session_context(session):
        return BokehModel(model)


def test_selected_seeds_an_empty_selection_at_attach(
    widget_session: Session,
) -> None:
    p, src = plot()
    w = widget(widget_session, p)
    emitted: List[object] = []
    detach = sb.SELECTED.attach(w, emitted.append)
    assert emitted == [[]]  # state-kind: seeded with the current selection
    src.selected.indices = [1, 2]
    assert emitted == [[], [1, 2]]
    detach()
    src.selected.indices = [0]
    assert emitted == [[], [1, 2]]


def test_selected_seeds_a_selection_made_before_attach(
    widget_session: Session,
) -> None:
    p, src = plot()
    src.selected.indices = [1, 2]
    w = widget(widget_session, p)
    emitted: List[object] = []
    sb.SELECTED.attach(w, emitted.append)
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


def test_event_callbacks_do_not_accumulate_across_attaches(
    widget_session: Session,
) -> None:
    # Every attach used to add a permanent plot.on_event() callback (bokeh
    # has no public removal), so re-renders accumulated dead closures on the
    # plot: N renders x M event accessors retained per plot (#418).
    p, _ = plot()
    w = widget(widget_session, p)
    for _ in range(3):
        detach = sb.TAPPED.attach(w, lambda raw: None)
        detach()
    assert len(p._event_callbacks["tap"]) == 1


def test_multiple_live_accessors_on_the_same_event_each_receive_events(
    widget_session: Session,
) -> None:
    p, _ = plot()
    w = widget(widget_session, p)
    a: List[object] = []
    b: List[object] = []
    detach_a = sb.TAPPED.attach(w, a.append)
    detach_b = sb.TAPPED.attach(w, b.append)
    assert len(p._event_callbacks["tap"]) == 1  # one fan-out callback, not two
    tap = Tap(model=p, x=1, y=2)
    p.document.callbacks.trigger_event(tap)
    assert a == [tap]
    assert b == [tap]
    detach_a()
    tap2 = Tap(model=p, x=3, y=4)
    p.document.callbacks.trigger_event(tap2)
    assert a == [tap]
    assert b == [tap, tap2]
    detach_b()


def test_detached_event_emits_are_not_invoked(widget_session: Session) -> None:
    p, _ = plot()
    w = widget(widget_session, p)
    stale: List[object] = []
    detach = sb.TAPPED.attach(w, stale.append)
    detach()
    p.document.callbacks.trigger_event(Tap(model=p, x=0, y=0))
    assert stale == []
    # A re-attach (e.g. a re-render) of the same event still receives events
    live: List[object] = []
    sb.TAPPED.attach(w, live.append)
    tap = Tap(model=p, x=1, y=2)
    p.document.callbacks.trigger_event(tap)
    assert live == [tap]
    assert stale == []


def test_the_event_registry_holds_plots_weakly(widget_session: Session) -> None:
    import gc
    import weakref

    p, src = plot()
    w = widget(widget_session, p)
    detach = sb.TAPPED.attach(w, lambda raw: None)
    detach()
    ref = weakref.ref(p)
    w.close()
    # src is a model in the same bokeh document, and every document model
    # strongly references the document (which references the plot), so it
    # must be dropped too
    del p, src, w, detach
    gc.collect()
    assert ref() is None


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
    assert r.selected() == []  # seeded at render
    out = r.selected_rows()
    assert isinstance(out, pd.DataFrame) and len(out) == 0
    src.selected.indices = [2, 0]
    assert r.selected() == [2, 0]
    assert r.selected_rows()["x"].tolist() == [3, 1]


def test_selected_rows_reflects_a_selection_made_before_the_first_read(
    widget_session: Session,
) -> None:
    from shinywidgets import render_bokeh

    p, src = plot()
    w = widget(widget_session, p)
    r = render_bokeh(rate_delay=0)
    r._widget = w  # stands in for _render()
    # The user selects before anything reads the accessor
    src.selected.indices = [2, 0]
    r._accessors.on_render(w)
    assert r.selected() == [2, 0]
    assert r.selected_rows()["x"].tolist() == [3, 1]


def test_selected_rows_readers_rerun_when_the_data_is_replaced(
    widget_session: Session,
) -> None:
    from shinywidgets import render_bokeh

    p, src = plot()
    w = widget(widget_session, p)
    r = render_bokeh(rate_delay=0)
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    r.selected_rows()  # already attached (and seeded) at render
    src.selected.indices = [0]
    reader = Context()
    with reader():
        assert r.selected_rows()["x"].tolist() == [1]
    # Same length, so the browser keeps the selected indices
    src.data = {"x": [7, 8, 9], "y": [4, 5, 6]}
    assert reader._invalidated
    assert r.selected_rows()["x"].tolist() == [7]


def test_selected_frame_drops_indices_past_the_end(widget_session: Session) -> None:
    p, src = plot()
    w = widget(widget_session, p)
    src.data = {"x": [1], "y": [4]}  # shrunk in place; the selection lags
    assert sb.selected_frame(w, [0, 2])["x"].tolist() == [1]


def test_tapped_and_zoomed_are_retained() -> None:
    assert sb.TAPPED.kind == "state"
    assert sb.ZOOMED.kind == "state"
    # The carve-out: source_data is an internal trigger whose reader
    # (selected_rows()) recomputes from the live document, so it keeps
    # event mechanics -- a stale value must not carry across re-renders.
    assert sb.SOURCE_DATA.kind == "event"


def test_zoomed_seeds_current_ranges(widget_session: Session) -> None:
    p, _ = plot()
    p.x_range.start, p.x_range.end = 2, 10
    p.y_range.start, p.y_range.end = -1, 5
    w = widget(widget_session, p)
    emitted: List[object] = []
    sb.attach_zoomed(w, emitted.append)
    seed = next(e for e in emitted if isinstance(e, RangesUpdate))
    assert (seed.x0, seed.x1, seed.y0, seed.y1) == (2, 10, -1, 5)


def test_zoomed_seed_reports_datetime_ranges_as_floats(
    widget_session: Session,
) -> None:
    # A datetime Range1d stores datetimes Python-side, but live RangesUpdate
    # events from the browser report floats (ms since epoch) -- the seed must
    # match, or a reader sees a different payload type before the first zoom
    import datetime as dt

    p, _ = plot()
    p.x_range.start = dt.datetime(2024, 1, 1)
    p.x_range.end = dt.datetime(2024, 2, 1)
    p.y_range.start, p.y_range.end = -1, 5
    w = widget(widget_session, p)
    emitted: List[object] = []
    sb.attach_zoomed(w, emitted.append)
    seed = next(e for e in emitted if isinstance(e, RangesUpdate))
    assert (seed.x0, seed.x1) == (1704067200000.0, 1706745600000.0)


def test_zoomed_skips_the_seed_when_ranges_are_unknown(
    widget_session: Session,
) -> None:
    # A default figure auto-fits browser-side: its ranges are NaN (numeric)
    # or browser-computed (categorical) at attach, so no seed is emitted
    p, _ = plot()
    w = widget(widget_session, p)
    emitted: List[object] = []
    sb.attach_zoomed(w, emitted.append)
    assert emitted == []

    q = figure(x_range=["a", "b"])
    wq = widget(widget_session, q)
    emitted_q: List[object] = []
    sb.attach_zoomed(wq, emitted_q.append)
    assert emitted_q == []
