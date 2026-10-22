from __future__ import annotations

import asyncio

import pytest
from shiny import Session, reactive
from shiny.reactive._core import Context
from shiny.session import session_context
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
