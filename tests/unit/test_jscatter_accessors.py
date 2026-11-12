from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import shinywidgets._jscatter as sj
from shiny import Session
from shiny.session import session_context

if TYPE_CHECKING:
    import jscatter


# A Scatter is jscatter's builder; its .widget is the JupyterScatter the
# renderer coerces to and the attach function receives. Widgets must be built
# inside a session (shinywidgets' construction hook requires one).
def scatter_widget(session: Session) -> object:
    import jscatter

    with session_context(session):
        return jscatter.Scatter(x=[1.0, 2.0, 3.0], y=[4.0, 5.0, 6.0]).widget


def test_selected_attach_seeds_and_emits(widget_session: Session) -> None:
    w = scatter_widget(widget_session)
    emitted: list[object] = []
    detach = sj.SELECTED.attach(w, emitted.append)
    assert len(emitted) == 1  # state accessors seed the current value
    assert list(emitted[0]) == []  # a fresh Scatter's selection is empty
    w.selection = np.array([2, 0], dtype=np.uint32)
    assert list(emitted[-1]) == [2, 0]
    detach()
    w.selection = np.array([1], dtype=np.uint32)
    assert list(emitted[-1]) == [2, 0]


def test_selected_not_ready_only_before_first_report() -> None:
    assert sj.is_unreported(None)
    assert not sj.is_unreported(np.array([], dtype=np.uint32))


def test_selected_dedupes_equal_empty_selections(widget_session: Session) -> None:
    # jscatter emits an empty array on lasso-nothing/deselect; an equal empty
    # echo must not republish (payloads_equal compares arrays up front)
    from shinywidgets import render_jscatter

    from tests.unit.test_accessors import spy_sets

    w = scatter_widget(widget_session)
    r = render_jscatter()
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    sets = spy_sets(r._accessors, "selected")
    assert list(r.selected()) == []
    n = len(sets)
    w.selection = np.array([], dtype=np.uint32)
    assert len(sets) == n


def test_selected_accessor_reads_positions(widget_session: Session) -> None:
    from shinywidgets import render_jscatter

    w = scatter_widget(widget_session)
    r = render_jscatter()
    r._widget = w  # stands in for _render(); see test_bokeh_accessors.py
    r._accessors.on_render(w)
    assert list(r.selected()) == []
    w.selection = np.array([1, 2], dtype=np.uint32)
    assert list(r.selected()) == [1, 2]


def scatter(session: Session) -> jscatter.Scatter:
    import jscatter

    df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [4.0, 5.0, 6.0], "c": list("abc")})
    with session_context(session):
        sc = jscatter.Scatter(data=df, x="x", y="y")
        sc.widget  # the JupyterScatter is built lazily, on first access
        return sc


def test_selected_rows_defaults_to_the_scatter_frame(widget_session: Session) -> None:
    from shinywidgets import render_jscatter

    sc = scatter(widget_session)
    r = render_jscatter()
    r._value = sc  # stands in for _render()
    r._widget = sc.widget
    r._accessors.on_render(sc.widget)
    assert len(r.selected_rows()) == 0
    sc.widget.selection = np.array([2, 0], dtype=np.uint32)
    out = r.selected_rows()
    assert isinstance(out, pd.DataFrame)
    assert out["c"].tolist() == ["c", "a"]  # selection order, not frame order


def test_selected_rows_explicit_frame_keeps_its_type(widget_session: Session) -> None:
    import polars as pl
    from shinywidgets import render_jscatter

    sc = scatter(widget_session)
    r = render_jscatter()
    r._value = sc
    r._widget = sc.widget
    r._accessors.on_render(sc.widget)
    sc.widget.selection = np.array([1], dtype=np.uint32)
    out = r.selected_rows(pl.DataFrame({"y": [4.0, 5.0, 6.0]}))
    assert isinstance(out, pl.DataFrame)
    assert out["y"].to_list() == [5.0]


def test_selected_rows_requires_a_frame_for_a_bare_widget(
    widget_session: Session,
) -> None:
    import pytest
    from shinywidgets import render_jscatter

    # A bare JupyterScatter (not built via Scatter) retains no data frame
    w = scatter_widget(widget_session)
    r = render_jscatter()
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    with pytest.raises(TypeError, match="df"):
        r.selected_rows()


def test_select_rows_at_selection_order_and_empty() -> None:
    from shinywidgets._utils import select_rows_at

    df = pd.DataFrame({"a": [10, 20, 30]})
    assert select_rows_at(df, [2, 0])["a"].tolist() == [30, 10]
    out = select_rows_at(df, [])
    assert len(out) == 0 and list(out.columns) == ["a"]
