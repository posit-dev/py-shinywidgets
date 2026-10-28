# ipyreact's define_module()/define_import_map() construct process-global
# dependency widgets (Module/ImportMap), usually at import time (e.g. by
# reactable-py). shinywidgets mirrors them into every session, like
# shared_lifetime() widgets, so the frontend models can register their ES
# modules with the import shim before any ipyreact widget needs them.

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Iterator
from typing import Any, TypeVar

import pytest
import shinywidgets._shinywidgets as sw
from shiny import App, Session, ui
from shiny._connection import MockConnection
from shiny.session import session_context

from tests.unit.conftest import widget_test_server

T = TypeVar("T")


def run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(scope="module")
def ipyreact() -> Iterator[Any]:
    # Importing ipyreact constructs its process-global ImportMap widget, which
    # our hook registers in SHARED_WIDGETS; don't let it leak into other test
    # modules (it would be opened in every session they create).
    before = dict(sw.SHARED_WIDGETS)
    mod = pytest.importorskip("ipyreact")
    try:
        yield mod
    finally:
        for model_id, w in list(sw.SHARED_WIDGETS.items()):
            if before.get(model_id) is not w:
                w.close()
                sw.SHARED_WIDGETS.pop(model_id, None)


@pytest.fixture
def other_session() -> Iterator[Session]:
    session = App(ui.page_fluid(), widget_test_server)._create_session(MockConnection())
    try:
        yield session
    finally:
        run(session.close())


def test_import_time_module_is_shared(ipyreact: Any, shared_state: None) -> None:
    # define_module() outside any session (e.g. reactable-py at import time)
    mod = ipyreact.define_module("shinywidgets_test_mod1", code="export default 1")
    assert sw.SHARED_WIDGETS.get(mod.model_id) is mod
    assert sw.is_process_global(mod)
    # its Layout, materialized while it was constructed, is shared too
    assert sw.SHARED_WIDGETS.get(mod.layout.model_id) is mod.layout


def test_ipyreact_import_map_widget_is_shared(
    ipyreact: Any, shared_state: None
) -> None:
    # ipyreact constructs this one at its own import time
    import ipyreact.importmap

    w = ipyreact.importmap._import_map_widget
    assert w is not None
    assert sw.SHARED_WIDGETS.get(w.model_id) is w
    assert sw.is_process_global(w)


def test_define_module_in_session_is_shared(
    ipyreact: Any,
    widget_session: Session,
    other_session: Session,
    shared_state: None,
) -> None:
    with session_context(widget_session):
        mod = ipyreact.define_module("shinywidgets_test_mod2", code="export default 1")
        assert sw.SHARED_WIDGETS.get(mod.model_id) is mod
        assert sw.is_process_global(mod)

    # The deferred open gives it a live comm in this session...
    from tests.unit.test_shared_widgets import flush

    flush()
    from shinywidgets._comm import ShinyComm

    assert isinstance(mod.comm, ShinyComm)

    # ...and a later session gets it too (fanned out over a SharedShinyComm)
    from shinywidgets._comm import SharedShinyComm

    sw.open_shared_in(mod, other_session)
    assert isinstance(mod.comm, SharedShinyComm)
    assert mod.comm.has_session(widget_session.id)
    assert mod.comm.has_session(other_session.id)


def test_init_session_adopts_sessionless_ipyreact_widgets(
    ipyreact: Any, widget_session: Session, shared_state: None
) -> None:
    mod = ipyreact.define_module("shinywidgets_test_mod3", code="export default 1")
    # Simulate a Module our construction hook never registered (ipyreact
    # imported before shinywidgets, or during a stub session: the import
    # doesn't re-run for the real session)
    sw.SHARED_WIDGETS.pop(mod.model_id, None)
    sw.SHARED_WIDGETS.pop(mod.layout.model_id, None)

    with session_context(widget_session):
        sw.init_session(widget_session)

    from shinywidgets._comm import SharedShinyComm

    assert sw.SHARED_WIDGETS.get(mod.model_id) is mod
    assert sw.SHARED_WIDGETS.get(mod.layout.model_id) is mod.layout
    assert isinstance(mod.comm, SharedShinyComm)
    assert mod.comm.has_session(widget_session.id)
