from __future__ import annotations

import asyncio
import importlib
import warnings
from collections.abc import Iterator

import pytest
import shinywidgets._shinywidgets as sw
from ipywidgets import HTML
from shiny import App, Inputs, Outputs, Session, reactive, ui
from shiny._connection import MockConnection
from shiny.session import session_context


def _widget_test_server(input: Inputs, output: Outputs, session: Session) -> None:
    pass


@pytest.fixture
def widget_session(monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    """
    A real (non-stub) Shiny session backed by a MockConnection.

    Using `App._create_session()` registers the session with the app so fixture
    teardown doesn't fail with an unrelated app-registry KeyError.
    """
    app = App(ui.page_fluid(), _widget_test_server)
    session = app._create_session(MockConnection())
    monkeypatch.setattr(sw, "SHINYWIDGETS_CDN_ONLY", True)
    # Session effects send busy-count messages when they're scheduled, which
    # requires a current event loop (a real Shiny app always runs with one).
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield session
    finally:
        asyncio.run(session.close())
        asyncio.set_event_loop(None)
        loop.close()


def test_shinywidgets_module_does_not_use_deprecated_widget_registry() -> None:
    # Regression: shinywidgets must not access `Widget.widgets`, which
    # ipywidgets deprecated in 8.0.3 (it warns on every external access).
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "error",
            message="Widget.widgets is deprecated",
            category=DeprecationWarning,
        )
        importlib.reload(sw)


def test_close_does_not_use_deprecated_widget_registry(
    widget_session: Session,
) -> None:
    # Regression: closing a widget must not access `Widget.widgets` (see above),
    # and the closed widget must not linger in the ipywidgets instance registry
    # (which would keep it alive forever).
    from ipywidgets.widgets.widget import _instances

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "error",
            message="Widget.widgets is deprecated",
            category=DeprecationWarning,
        )
        with session_context(widget_session):
            widget = HTML(value="gone")
            model_id = widget.model_id
            asyncio.run(reactive.flush())
            widget.close()
            asyncio.run(reactive.flush())
    assert model_id not in sw.WIDGET_INSTANCE_MAP
    assert model_id not in _instances
