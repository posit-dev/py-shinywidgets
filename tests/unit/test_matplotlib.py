from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING, cast

import matplotlib.pyplot as plt
import pytest
from ipywidgets import Widget
from matplotlib._pylab_helpers import Gcf
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, ResizeEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure, SubFigure
from mpl_toolkits.mplot3d import Axes3D
from shiny import App, Session, reactive, ui
from shiny._connection import MockConnection
from shiny.reactive import Context
from shiny.session import session_context
from shiny.session._session import AppSession
from shinywidgets import as_widget, session_lifetime
from shinywidgets._comm import ShinyComm
from shinywidgets._render_widget_base import WidgetRenderContext, is_closed_widget

from tests.unit.conftest import widget_test_server

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


def test_seaborn_grid_coerced_via_its_figure(widget_session: Session) -> None:
    # seaborn's figure-level functions (e.g., relplot()) return a Grid that
    # holds its figure (seaborn isn't a test dependency, so mimic one)
    figure = Figure()
    grid = SeabornGrid(figure)

    with session_context(widget_session):
        widget = as_widget(grid)

    assert cast("Canvas", widget).figure is figure


def test_returned_canvas_gets_figure_manager(widget_session: Session) -> None:
    with session_context(widget_session):
        canvas_type = type(cast("Canvas", as_widget(Figure())))
        canvas = canvas_type(Figure())
        assert canvas.manager is None

        assert as_widget(canvas) is canvas
        # ipympl's browser messages (e.g., resize) go through the manager
        assert canvas.manager is not None


@pytest.mark.parametrize("returned", ["figure", "axes", "canvas"])
def test_pyplot_figure_leaves_pyplot_at_coercion(
    returned: str, widget_session: Session
) -> None:
    # pyplot's current figure is shared by every output and session in the
    # process, so a live figure left there can be drawn into by another
    # session's plt.gca() (e.g., a seaborn call without ax=)
    with session_context(widget_session):
        canvas_type = type(cast("Canvas", as_widget(Figure())))
        figure, axes = plt.subplots()
        if returned == "figure":
            x: object = figure
        elif returned == "axes":
            x = axes
        else:
            x = canvas_type(figure)
        canvas = cast("Canvas", as_widget(x))

    assert not plt.fignum_exists(figure.number)
    assert all(m.canvas.figure is not figure for m in Gcf.get_all_fig_managers())
    assert figure.canvas is canvas
    assert canvas.comm is not None


def test_canvas_works_after_leaving_pyplot(widget_session: Session) -> None:
    with session_context(widget_session):
        figure, axes = plt.subplots()
        axes.plot([0, 10], [0, 10])
        canvas = cast("Canvas", as_widget(figure))
        assert not plt.fignum_exists(figure.number)

        presses: list[Event] = []
        canvas.mpl_connect("button_press_event", presses.append)
        xlim = axes.get_xlim()

        def send(content: dict[str, object]) -> None:
            canvas._handle_message(canvas, content, [])

        def mouse(type: str, x: float, y: float, buttons: int) -> dict[str, object]:
            return {
                "type": type,
                "x": x,
                "y": y,
                "button": 0,
                "buttons": buttons,
                "modifiers": [],
            }

        send({"type": "toolbar_button", "name": "zoom"})
        send(mouse("button_press", 200, 200, 1))
        send(mouse("motion_notify", 300, 300, 1))
        send(mouse("button_release", 300, 300, 0))
        send({"type": "resize", "width": 300, "height": 200})

    assert figure.canvas is canvas
    assert len(presses) == 1
    assert axes.get_xlim() != xlim
    assert tuple(figure.get_size_inches() * figure.dpi) == (300, 200)


def test_pyplot_figure_coercion_fires_no_resize_event(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # On a HiDPI screen, a GUI backend (e.g., macosx) doubles a pyplot figure's
    # dpi and resizes its window (firing resize_event) when the dpi changes. A
    # resize_event callback that reads a reactive value would then run inside
    # the render and invalidate it, re-rendering forever.
    figure = plt.figure(dpi=100)
    figure.canvas._set_device_pixel_ratio(2)
    manager = figure.canvas.manager
    assert manager is not None

    def resize_window(width: int, height: int) -> None:
        ResizeEvent("resize_event", figure.canvas)._process()

    monkeypatch.setattr(manager, "resize", resize_window)
    resizes: list[Event] = []
    figure.canvas.mpl_connect("resize_event", resizes.append)

    with session_context(widget_session):
        as_widget(figure)

    assert resizes == []
    assert figure.dpi == 100


def test_figure_stays_live_when_ipympl_is_pyplots_backend() -> None:
    # With ipympl as pyplot's backend, pyplot's figure manager owns the very
    # canvas that gets displayed, and plt.close() would close that widget
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
with session_context(session):
    plt.switch_backend("module://ipympl.backend_nbagg")
    figure = plt.figure()
    canvas = figure.canvas
    assert as_widget(figure) is canvas

assert not plt.fignum_exists(figure.number)
assert canvas.comm is not None, "canvas was closed"
assert canvas.manager is not None
"""
    env = {**os.environ, "MPLBACKEND": "agg"}
    subprocess.run([sys.executable, "-c", script], check=True, env=env)


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


@pytest.mark.parametrize("coerced", [True, False])
def test_open_sends_initial_image(
    coerced: bool, widget_session: Session, monkeypatch: pytest.MonkeyPatch
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
        canvas_type = type(cast("Canvas", as_widget(Figure())))
        # e.g., a Canvas placed directly in a container widget
        canvas = as_widget(Figure()) if coerced else canvas_type(Figure())
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


def test_draw_error_raised_at_coercion(widget_session: Session) -> None:
    # Raised by the render (an output error) rather than by the deferred comm
    # open (an effect error, which ends the session)
    figure = Figure()
    figure.subplots().set_title(r"$\badcommand{x}$")

    with session_context(widget_session):
        with pytest.raises(ValueError, match="badcommand"):
            as_widget(figure)
        # The failed canvas never opens (opening would draw it again)
        asyncio.get_event_loop().run_until_complete(reactive.flush())

    assert isinstance(widget_session, AppSession)
    assert not widget_session._has_run_session_ended_tasks


def test_draw_error_on_live_canvas_leaves_it_open(widget_session: Session) -> None:
    # A reused canvas may already be displayed by another output in the same
    # session (its comm is open). A failed redraw must propagate to this render
    # without closing the canvas out from under the other output.
    figure = Figure()
    axes = figure.subplots()
    axes.plot([0, 1])

    with session_context(widget_session):
        canvas = cast("Canvas", as_widget(figure))
        asyncio.get_event_loop().run_until_complete(reactive.flush())
        assert isinstance(canvas.comm, ShinyComm)

        axes.set_title(r"$\badcommand{x}$")
        with pytest.raises(ValueError, match="badcommand"):
            as_widget(figure)

    assert isinstance(canvas.comm, ShinyComm)
    assert not is_closed_widget(canvas)


def test_mutation_after_coercion_is_drawn_again(widget_session: Session) -> None:
    # A canvas can be coerced (drawing its first image) and then have its
    # figure changed before it's returned. The cached image is stale then, so
    # the second coercion draws again -- refreshing the image and raising a
    # draw-time error in the new content at the render.
    figure = Figure()
    axes = figure.subplots()
    axes.plot([0, 1])

    with session_context(widget_session):
        canvas = cast("Canvas", as_widget(figure))
        assert canvas._data_url

        axes.set_title("after coercion")
        canvas2 = cast("Canvas", as_widget(figure))
        assert canvas2 is canvas

        axes.set_title(r"$\badcommand{x}$")
        with pytest.raises(ValueError, match="badcommand"):
            as_widget(figure)
        asyncio.get_event_loop().run_until_complete(reactive.flush())

    assert isinstance(widget_session, AppSession)
    assert not widget_session._has_run_session_ended_tasks


def test_foreign_canvas_rejected_before_draw(widget_session: Session) -> None:
    # A module-level cached figure returned from another session's render is
    # rejected by the renderer -- but coercion draws a reused canvas first,
    # which would update (or, on a draw error, close) the owner's live canvas.
    # The rejection must happen before that draw.
    other = App(ui.page_fluid(), widget_test_server)._create_session(MockConnection())
    try:
        with session_context(other):
            figure = Figure()
            axes = figure.subplots()
            axes.plot([0, 1])
            canvas = cast("Canvas", as_widget(figure))
        image = canvas._data_url

        with session_context(widget_session):
            axes.set_title("changed")
            with pytest.raises(RuntimeError, match="another Shiny session"):
                as_widget(figure)

        assert canvas._data_url == image
        assert not is_closed_widget(canvas)
    finally:
        asyncio.get_event_loop().run_until_complete(other.close())


def test_first_draw_callbacks_dont_invalidate_the_render(
    widget_session: Session,
) -> None:
    # The first draw happens inside the render, and fires callbacks (here,
    # xlim_changed from autoscaling). One that both reads and sets a reactive
    # value mustn't make the render depend on it, or it would re-render forever.
    count = reactive.value(0)
    figure = Figure()
    axes = figure.subplots()
    axes.plot([0, 1])
    axes.callbacks.connect("xlim_changed", lambda _: count.set(count.get() + 1))

    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            as_widget(figure)

    with reactive.isolate():
        assert count.get() > 0
    assert not context._invalidated


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


class SeabornGrid:
    __module__ = "seaborn.axisgrid"

    def __init__(self, figure: Figure) -> None:
        self.figure = figure
