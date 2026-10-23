from __future__ import annotations

import pytest
import shinywidgets._shinywidgets as sw
from packaging.version import Version
from shiny import Session
from shiny.session import session_context
from shinywidgets import as_widget

plotly = pytest.importorskip("plotly")

import plotly.graph_objects as go  # noqa: E402


@pytest.fixture
def old_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    # The dev/test environments install plotly >= 5.12, so fake an older
    # install to exercise the unsupported-version guard (plotly < 5.12's
    # FigureWidget frontend predates ipywidgets 8 support, #332)
    monkeypatch.setattr(sw, "_plotly_version", lambda: Version("5.11.0"))


def test_figurewidget_with_old_plotly_explains(
    widget_session: Session, old_plotly: None
) -> None:
    with session_context(widget_session):
        with pytest.raises(RuntimeError) as excinfo:
            go.FigureWidget(go.Scatter(x=[1], y=[1]))

    msg = str(excinfo.value)
    assert "plotly >= 5.12" in msg
    assert "plotly 5.11.0" in msg
    assert "blank" in msg
    assert "pip install -U plotly" in msg
    assert "0.8.2" in msg


def test_as_widget_figure_with_old_plotly_explains(
    widget_session: Session, old_plotly: None
) -> None:
    # Coercing a go.Figure constructs a FigureWidget, which hits the same guard
    with session_context(widget_session):
        with pytest.raises(RuntimeError, match="plotly >= 5.12"):
            as_widget(go.Figure(go.Scatter(x=[1], y=[1])))


def test_unsupported_plotly_version(
    monkeypatch: pytest.MonkeyPatch, old_plotly: None
) -> None:
    class FakePlotlyWidget:
        pass

    FakePlotlyWidget.__module__ = "plotly.basewidget"

    class NotAWidget:
        pass

    # The guard only applies to plotly widgets (checked via the class MRO)
    assert sw.unsupported_plotly_version(FakePlotlyWidget()) is not None  # type: ignore
    assert sw.unsupported_plotly_version(NotAWidget()) is None  # type: ignore

    # plotly 5.12+ (the first with an ipywidgets-8-compatible frontend) is fine
    monkeypatch.setattr(sw, "_plotly_version", lambda: Version("5.12.0"))
    assert sw.unsupported_plotly_version(FakePlotlyWidget()) is None  # type: ignore


def test_plotly_widget_ok_when_supported(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sw, "_plotly_version", lambda: Version("5.24.1"))
    with session_context(widget_session):
        w = go.FigureWidget(go.Scatter(x=[1], y=[1]))
    assert sw.unsupported_plotly_version(w) is None
    w.close()
