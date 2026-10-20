"""
For each way a widget can be closed (widget-initiated, comm-initiated,
session-initiated): shinywidgets itself never calls a widget's close() an extra
time, nothing raises, and the widget ends up out of the instance registry.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

import pytest
from ipywidgets import HTML
from ipywidgets.widgets.widget import _instances
from shiny import Session, reactive
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets._render_widget_base import WidgetRenderContext, is_closed_widget

T = TypeVar("T")


def run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.get_event_loop().run_until_complete(coro)


def flush() -> None:
    run(reactive.flush())


class CleanupWidget(HTML):
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.cleanup_calls = 0
        super().__init__(*args, **kwargs)

    def close(self) -> None:
        super().close()
        self.cleanup_calls += 1


def test_widget_initiated_close_is_not_repeated_by_a_later_sweep(
    widget_session: Session,
) -> None:
    """
    Trigger: the user calls widget.close() themselves.

    (Calling close() multiple times in a row and checking cleanup still ran
    once would test the stack's close-guard, which plain ipywidgets doesn't
    have and this PR doesn't port -- see this module's docstring. What matters
    here is that shinywidgets' own later sweep doesn't call close() again.)
    """
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            widget = CleanupWidget(value="resource")
        flush()

        widget.close()
        assert widget.cleanup_calls == 1

        # The render later invalidates (e.g. a re-render); shinywidgets must not
        # call close() again on a widget the user already closed.
        context.invalidate()
        flush()

    assert widget.cleanup_calls == 1
    assert is_closed_widget(widget)
    assert not any(w is widget for w in _instances.values())


def test_session_initiated_close_runs_cleanup_once(widget_session: Session) -> None:
    """Trigger: the session ends while the widget is still open."""
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            widget = CleanupWidget(value="resource")
        flush()

        run(widget_session.close())

    assert widget.cleanup_calls == 1
    assert is_closed_widget(widget)
    assert not any(w is widget for w in _instances.values())


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known gap: ipywidgets' Widget never "
        "registers comm.on_close(), so closing only the comm (without calling "
        "widget.close()) never runs the widget's own close() or removes it from "
        "the registry."
    ),
)
def test_comm_initiated_close_runs_widget_cleanup(widget_session: Session) -> None:
    """Trigger: something closes the comm directly, not via widget.close()."""
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            widget = CleanupWidget(value="resource")
        flush()

        assert widget.comm is not None
        widget.comm.close()
        flush()

    assert widget.cleanup_calls == 1
    assert widget.model_id not in _instances
    assert is_closed_widget(widget)
