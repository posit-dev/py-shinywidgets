from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING, cast

import pytest
from ipywidgets import Widget
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure, SubFigure
from mpl_toolkits.mplot3d import Axes3D
from shiny import Session, reactive
from shiny.reactive import Context
from shiny.session import session_context
from shiny.session._session import AppSession
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


def test_coercion_undoes_previous_canvas_pixel_ratio(widget_session: Session) -> None:
    # GUI backends (e.g., macosx on a HiDPI screen) scale the figure's dpi by
    # their screen's pixel ratio
    figure = Figure(dpi=100)
    FigureCanvasAgg(figure)._set_device_pixel_ratio(2)
    assert figure.dpi == 200

    with session_context(widget_session):
        canvas = cast("Canvas", as_widget(figure))
    assert figure.dpi == 100

    # ipympl applies the browser's pixel ratio instead
    canvas._set_device_pixel_ratio(2)
    assert figure.dpi == 200


def test_open_sends_initial_image(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The frontend's first paint comes from _data_url, which ipympl only sets
    # in its display hook
    messages: list[str] = []

    async def send_custom_message(type: str, message: object) -> None:
        if type == "shinywidgets_comm_open":
            assert isinstance(message, str)
            messages.append(message)

    monkeypatch.setattr(widget_session, "send_custom_message", send_custom_message)
    assert isinstance(widget_session, AppSession)
    with session_context(widget_session):
        canvas = as_widget(Figure())
        asyncio.get_event_loop().run_until_complete(reactive.flush())
        asyncio.get_event_loop().run_until_complete(
            widget_session._flush_callbacks.invoke()
        )

    state = next(
        msg["content"]["data"]["state"]
        for msg in map(json.loads, messages)
        if msg["content"]["comm_id"] == canvas.model_id
    )
    assert state["_data_url"].startswith("data:image/png;base64,")


def test_coercion_preserves_pyplot_backend() -> None:
    # ipympl selects itself as pyplot's backend when first imported, so this
    # must run in a process that hasn't imported it yet
    script = """
import asyncio

import matplotlib.pyplot as plt
from shiny import App, ui
from shiny._connection import MockConnection
from shiny.session import session_context
from shinywidgets import as_widget

asyncio.set_event_loop(asyncio.new_event_loop())
session = App(ui.page_fluid(), lambda input, output, session: None)._create_session(
    MockConnection()
)
unrelated = plt.figure()
with session_context(session):
    as_widget(plt.figure())

assert plt.get_backend() == "agg", plt.get_backend()
assert plt.fignum_exists(unrelated.number)
"""
    env = {**os.environ, "MPLBACKEND": "agg"}
    subprocess.run([sys.executable, "-c", script], check=True, env=env)


class CustomAxes(Axes):
    pass
