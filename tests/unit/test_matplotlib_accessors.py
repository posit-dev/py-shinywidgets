from __future__ import annotations

from typing import List, Optional

import pytest
import shinywidgets._matplotlib as sm
import shinywidgets._render_widget as rw
from matplotlib.backend_bases import MouseButton, MouseEvent, PickEvent
from matplotlib.figure import Figure
from shiny import Session
from shiny.session import session_context
from shinywidgets._as_widget import backend_selection_suppressed


@pytest.fixture
def canvas(widget_session: Session):
    # Import ipympl without letting it select itself as pyplot's backend (it
    # would make later tests' plt.figure() calls construct ipympl widgets)
    with backend_selection_suppressed():
        from ipympl.backend_nbagg import Canvas, FigureManager

    with session_context(widget_session):
        figure = Figure()
        ax = figure.subplots()
        (line,) = ax.plot([0, 1, 2], [0, 1, 0], picker=5)
        cv = Canvas(figure=figure)
        # The render path always gives the canvas a manager, which wires up
        # the toolbar (its `mode` tells a click from a pan/zoom drag)
        manager = FigureManager(cv, 0)
    try:
        yield figure, ax, line, cv
    finally:
        from matplotlib._pylab_helpers import Gcf

        Gcf.destroy(manager.num)


def press(cv, x: float = 100, y: float = 100, inaxes: Optional[object] = None) -> None:
    event = MouseEvent("button_press_event", cv, x, y, button=MouseButton.LEFT)
    event.inaxes = inaxes
    cv.callbacks.process("button_press_event", event)


def test_clicked_emits_plain_clicks_only(canvas) -> None:
    figure, ax, _, cv = canvas
    emitted: List[object] = []
    detach = sm.CLICKED.attach(cv, emitted.append)
    press(cv, inaxes=ax)
    assert len(emitted) == 1 and isinstance(emitted[0], MouseEvent)
    press(cv, inaxes=None)  # click outside any axes: not a click
    assert len(emitted) == 1
    cv.toolbar.mode = "zoom rect"  # a drag in a toolbar mode is not a click
    press(cv, inaxes=ax)
    assert len(emitted) == 1
    cv.toolbar.mode = ""
    detach()
    press(cv, inaxes=ax)
    assert len(emitted) == 1


def test_clicked_detach_disconnects_the_cid(canvas) -> None:
    # A cached Figure rendered twice must not stack handlers (Review Focus 2)
    _, ax, _, cv = canvas
    emitted: List[object] = []
    detach = sm.CLICKED.attach(cv, emitted.append)
    detach()
    detach = sm.CLICKED.attach(cv, emitted.append)
    press(cv, inaxes=ax)
    assert len(emitted) == 1
    detach()


def test_picked_emits_pick_events(canvas) -> None:
    _, ax, line, cv = canvas
    emitted: List[object] = []
    detach = sm.PICKED.attach(cv, emitted.append)
    mouse = MouseEvent("button_press_event", cv, 100, 100, button=MouseButton.LEFT)
    cv.callbacks.process(
        "pick_event", PickEvent("pick_event", cv, mouse, line, ind=[1])
    )
    assert len(emitted) == 1 and emitted[0].ind == [1]
    detach()


def test_limits_seeds_and_follows_zooms(canvas) -> None:
    _, ax, _, cv = canvas
    emitted: List[object] = []
    detach = sm.LIMITS.attach(cv, emitted.append)
    assert len(emitted) == 1  # seeded with the current limits at attach
    ax.set_xlim(0.5, 0.75)
    assert emitted[-1] == (((0.5, 0.75), tuple(ax.get_ylim())),)
    ax.set_ylim(-1, 1)
    assert emitted[-1] == (((0.5, 0.75), (-1.0, 1.0)),)
    detach()
    ax.set_xlim(0, 1)
    assert emitted[-1] == (((0.5, 0.75), (-1.0, 1.0)),)


def test_renderer_methods_read_through_the_accessors(canvas) -> None:
    _, ax, _, cv = canvas
    r = rw.render_matplotlib()
    r._widget = cv  # stands in for _render()
    r._accessors.on_render(cv)
    assert r.clicked() is None
    press(cv, inaxes=ax)
    assert isinstance(r.clicked(), MouseEvent)
    assert r.limits() == (tuple(ax.get_xlim()), tuple(ax.get_ylim()))
    with pytest.raises(IndexError, match="1 axes"):
        r.limits(ax=1)


def test_plotnine_shares_the_clicked_spec() -> None:
    assert rw.render_plotnine._accessor_specs == (sm.CLICKED,)
    assert (
        rw.render_plotnine._accessor_specs[0] is rw.render_matplotlib._accessor_specs[0]
    )
