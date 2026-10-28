from __future__ import annotations

import asyncio

import pytest
import shinywidgets._render_widget as rw
from ipywidgets.widgets.widget import Widget
from shiny import Session
from shiny.session import session_context
from shinywidgets._as_widget import as_widget
from shinywidgets._render_widget_base import set_layout_defaults

pytest.importorskip("numpy")
rr = pytest.importorskip("rerun")
pytest.importorskip("rerun_notebook")

from rerun.notebook import Viewer  # noqa: E402
from rerun_notebook import Viewer as RerunNotebookViewer  # noqa: E402


def make_viewer(**kwargs) -> Viewer:
    rec = rr.RecordingStream(application_id="test_rerun")
    rec.log("points", rr.Points3D([[0, 0, 0], [1, 1, 1]]))
    return Viewer(recording=rec, **kwargs)


def test_as_widget_rerun_unwraps_high_level_viewer(widget_session: Session) -> None:
    with session_context(widget_session):
        v = make_viewer()
        w = as_widget(v)
    assert isinstance(w, RerunNotebookViewer)
    assert w is v._viewer


def test_as_widget_rerun_passes_through_notebook_widget(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        v = make_viewer()
        assert as_widget(v._viewer) is v._viewer


def test_as_widget_rerun_rejects_other_rerun_objects() -> None:
    rec = rr.RecordingStream(application_id="test_rerun_reject")
    with pytest.raises(TypeError, match="rerun.notebook.Viewer"):
        as_widget(rec)


def test_rerun_layout_defaults_treat_640x480_as_unset(widget_session: Session) -> None:
    with session_context(widget_session):
        w = make_viewer()._viewer
        assert (w._width, w._height) == (640, 480)
        _, fill = set_layout_defaults(w)
    assert fill is True
    assert (w._width, w._height) == ("auto", "auto")


def test_rerun_layout_defaults_respect_explicit_height(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        w = make_viewer(width=640, height=300)._viewer
        _, fill = set_layout_defaults(w)
    # width default is still rewritten, but an explicit height opts out of fill
    assert fill is False
    assert (w._width, w._height) == ("auto", 300)


def test_rerun_layout_defaults_respect_explicit_size(widget_session: Session) -> None:
    with session_context(widget_session):
        w = make_viewer(width=500, height=300)._viewer
        _, fill = set_layout_defaults(w)
    assert fill is False
    assert (w._width, w._height) == (500, 300)


def test_render_rerun_coerces_high_level_viewer(widget_session: Session) -> None:
    r = rw.render_rerun()

    @r
    def _():  # noqa: ANN202
        return make_viewer()

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert isinstance(res, dict)
    assert isinstance(r.widget, RerunNotebookViewer)
    assert res["widget_pkg"] == "rerun_notebook"


def test_render_rerun_passes_through_notebook_widget(widget_session: Session) -> None:
    r = rw.render_rerun()

    with session_context(widget_session):
        w = make_viewer()._viewer

        @r
        def _():  # noqa: ANN202
            return w

        asyncio.run(r._render())

    assert r.widget is w


def test_render_rerun_widget_is_a_widget(widget_session: Session) -> None:
    with session_context(widget_session):
        assert isinstance(make_viewer()._viewer, Widget)
