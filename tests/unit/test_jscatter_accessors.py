from __future__ import annotations

import numpy as np
import shinywidgets._jscatter as sj
from shiny import Session
from shiny.session import session_context


# A Scatter is jscatter's builder; its .widget is the JupyterScatter the
# renderer coerces to and the attach function receives. Widgets must be built
# inside a session (shinywidgets' construction hook requires one).
def scatter_widget(session: Session) -> object:
    import jscatter

    with session_context(session):
        return jscatter.Scatter(x=[1.0, 2.0, 3.0], y=[4.0, 5.0, 6.0]).widget


def test_selection_attach_seeds_and_emits(widget_session: Session) -> None:
    w = scatter_widget(widget_session)
    emitted: list[object] = []
    detach = sj.SELECTION.attach(w, emitted.append)
    assert len(emitted) == 1  # state accessors seed the current value
    assert list(emitted[0]) == []  # a fresh Scatter's selection is empty
    w.selection = np.array([2, 0], dtype=np.uint32)
    assert list(emitted[-1]) == [2, 0]
    detach()
    w.selection = np.array([1], dtype=np.uint32)
    assert list(emitted[-1]) == [2, 0]


def test_selection_not_ready_only_before_first_report() -> None:
    assert sj.is_unreported(None)
    assert not sj.is_unreported(np.array([], dtype=np.uint32))


def test_selection_accessor_reads_positions(widget_session: Session) -> None:
    from shinywidgets import render_jscatter

    w = scatter_widget(widget_session)
    r = render_jscatter()
    r._widget = w  # stands in for _render(); see test_bokeh_accessors.py
    r._accessors.on_render(w)
    assert list(r.selection()) == []
    w.selection = np.array([1, 2], dtype=np.uint32)
    assert list(r.selection()) == [1, 2]
