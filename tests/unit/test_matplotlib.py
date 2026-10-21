from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from ipywidgets import Widget
from matplotlib.axes import Axes
from matplotlib.figure import Figure, SubFigure
from mpl_toolkits.mplot3d import Axes3D
from shiny import Session
from shiny.reactive import Context
from shiny.session import session_context
from shinywidgets import as_widget, session_lifetime
from shinywidgets._render_widget_base import WidgetRenderContext

if TYPE_CHECKING:
    from ipympl.backend_nbagg import Canvas


@pytest.mark.parametrize("kind", ["3d", "custom", "subfigure", "nested-subfigure"])
def test_axes_coercion_uses_root_figure(kind: str, widget_session: Session) -> None:
    figure = Figure()
    if kind == "3d":
        axes = figure.add_subplot(axes_class=Axes3D)
    elif kind == "custom":
        axes = figure.add_subplot(axes_class=CustomAxes)
    elif kind == "subfigure":
        subfigure = figure.subfigures(1, 1)
        assert isinstance(subfigure, SubFigure)
        axes = subfigure.subplots()
    else:
        subfigure = figure.subfigures(1, 1)
        assert isinstance(subfigure, SubFigure)
        nested = subfigure.subfigures(1, 1)
        assert isinstance(nested, SubFigure)
        axes = nested.subplots()

    with session_context(widget_session):
        widget = as_widget(axes)

    assert isinstance(widget, Widget)
    assert cast("Canvas", widget).figure is figure
    assert figure.canvas is widget


def test_existing_canvas_is_reused_with_its_settings(widget_session: Session) -> None:
    with session_context(widget_session):
        figure = Figure()
        canvas = cast("Canvas", as_widget(figure))
        manager = canvas.manager
        canvas.header_visible = False
        canvas.toolbar_visible = False
        canvas.resizable = False

        assert as_widget(figure) is canvas
        assert canvas.manager is manager
        assert canvas.header_visible is False
        assert canvas.toolbar_visible is False
        assert canvas.resizable is False


def test_closed_canvas_can_be_replaced_for_the_same_figure(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        figure = Figure()
        context = Context()
        with context(), WidgetRenderContext():
            first = as_widget(figure)
        context.invalidate()

        second = as_widget(figure)
        assert second is not first
        assert cast("Canvas", second).figure is figure


@pytest.mark.parametrize("with_manager", [True, False])
def test_reusing_session_canvas_preserves_its_lifetime(
    with_manager: bool, widget_session: Session
) -> None:
    with session_context(widget_session):
        figure = Figure()
        canvas_type = type(cast("Canvas", as_widget(Figure())))
        with session_lifetime():
            canvas = (
                cast("Canvas", as_widget(figure))
                if with_manager
                else canvas_type(figure)
            )

        context = Context()
        with context(), WidgetRenderContext():
            assert as_widget(figure) is canvas
        assert canvas.manager is not None
        toolbar = canvas.toolbar
        assert isinstance(toolbar, Widget)
        context.invalidate()

        assert canvas.comm is not None
        assert toolbar.comm is not None
        assert as_widget(figure) is canvas


class CustomAxes(Axes):
    pass
