from __future__ import annotations

import asyncio

import pytest
from shiny import Session, reactive
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets import render_k3d
from shinywidgets._comm import ShinyComm
from shinywidgets._render_widget_base import WidgetRenderContext
from shinywidgets._shinywidgets import COMM_MANAGERS


def flush() -> None:
    asyncio.get_event_loop().run_until_complete(reactive.flush())


def test_rerender_closes_k3d_plot_comm(widget_session: Session) -> None:
    # k3d's Plot.close() doesn't call Widget.close(), so without a workaround
    # the old plot's comm (and the browser's model) outlives every re-render
    k3d = pytest.importorskip("k3d")

    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            plot = k3d.plot()
            plot += k3d.points([[0, 0, 0]])
        flush()
        comm = plot.comm
        assert isinstance(comm, ShinyComm)

        context.invalidate()
        flush()

    assert comm._closed
    assert comm.comm_id not in COMM_MANAGERS[widget_session.id].comms


def test_rerender_closes_k3d_plot_subclass_comm(widget_session: Session) -> None:
    # A user-defined Plot subclass reports its own module, but inherits k3d's
    # non-closing close(), so the workaround must reach it through the MRO
    pytest.importorskip("k3d")
    from k3d.plot import Plot

    class MyPlot(Plot):
        pass

    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            plot = MyPlot()
        flush()
        comm = plot.comm
        assert isinstance(comm, ShinyComm)

        context.invalidate()
        flush()

    assert comm._closed
    assert comm.comm_id not in COMM_MANAGERS[widget_session.id].comms


def test_render_k3d_puts_a_bare_drawable_on_a_plot(widget_session: Session) -> None:
    # A drawable draws nothing by itself (Jupyter displays it on a new plot)
    k3d = pytest.importorskip("k3d")

    with session_context(widget_session):
        points = k3d.points([[0, 0, 0]])
        plot = render_k3d()._as_widget(points)
        assert isinstance(plot, k3d.Plot)
        assert list(plot.objects) == [points]

        group = k3d.points([[0, 0, 0]]) + k3d.points([[1, 1, 1]])
        assert len(render_k3d()._as_widget(group).objects) == 2

        existing = k3d.plot()
        assert render_k3d()._as_widget(existing) is existing
