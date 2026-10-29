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

    # The deferred open fans it out to every live session (here just this
    # one; the other session hasn't initialized shinywidgets yet)
    from tests.unit.test_shared_widgets import flush

    flush()
    from shinywidgets._comm import SharedShinyComm

    assert isinstance(mod.comm, SharedShinyComm)
    assert mod.comm.has_session(widget_session.id)

    # ...and a session initialized later gets it too
    sw.open_shared_in(mod, other_session)
    assert mod.comm.has_session(widget_session.id)
    assert mod.comm.has_session(other_session.id)


def test_define_module_opens_in_existing_sessions(
    ipyreact: Any,
    widget_session: Session,
    other_session: Session,
    shared_state: None,
) -> None:
    # Both sessions are already initialized when the module is defined. A
    # consumer in the other session waits on the module by name (there is no
    # widget reference the render-time walk could follow), so the deferred
    # open must fan out to it immediately.
    sw.init_session(other_session)
    with session_context(widget_session):
        mod = ipyreact.define_module("shinywidgets_test_mod4", code="export default 1")
    from tests.unit.test_shared_widgets import flush

    flush()
    from shinywidgets._comm import SharedShinyComm

    assert isinstance(mod.comm, SharedShinyComm)
    assert mod.comm.has_session(widget_session.id)
    assert mod.comm.has_session(other_session.id)


def test_define_module_opens_in_sessions_initialized_before_flush(
    ipyreact: Any,
    widget_session: Session,
    other_session: Session,
    shared_state: None,
) -> None:
    # A and B are initialized, A defines a module, and C initializes before
    # A's deferred open runs: C's init_session() adopts the module, giving
    # it a SharedShinyComm. A's deferred open must still fan the module out
    # to B (open_shared_in() is idempotent per session), not return early at
    # the shared-comm check.
    sw.init_session(other_session)
    with session_context(widget_session):
        mod = ipyreact.define_module("shinywidgets_test_mod7", code="export default 1")
    third_session = App(ui.page_fluid(), widget_test_server)._create_session(
        MockConnection()
    )
    try:
        # C's first widget initializes its session, which adopts the module
        import ipywidgets

        with session_context(third_session):
            ipywidgets.IntSlider()
        from shinywidgets._comm import SharedShinyComm

        assert isinstance(mod.comm, SharedShinyComm)
        assert mod.comm.has_session(third_session.id)

        from tests.unit.test_shared_widgets import flush

        flush()
        assert mod.comm.has_session(widget_session.id)
        assert mod.comm.has_session(other_session.id)
        assert mod.comm.has_session(third_session.id)
    finally:
        run(third_session.close())


def test_sessionless_define_module_opens_on_consumer_render(
    ipyreact: Any, widget_session: Session, shared_state: None
) -> None:
    # A sessionless define_module() after the session initialized gets no
    # construction-time fan-out: rendering a consumer is what must open the
    # module in the session (its frontend waits on the module by name).
    with session_context(widget_session):
        sw.init_session(widget_session)
    mod = ipyreact.define_module("shinywidgets_test_mod8", code="export default 1")
    from shinywidgets._comm import SharedShinyComm, ShinyComm

    assert not isinstance(mod.comm, (ShinyComm, SharedShinyComm))

    with session_context(widget_session):
        consumer = ipyreact.Widget(_esm="export default 1")
        sw.open_process_global_widgets(consumer, widget_session)
    assert isinstance(mod.comm, SharedShinyComm)
    assert mod.comm.has_session(widget_session.id)


def test_registry_ignores_client_state_writes(
    ipyreact: Any, widget_session: Session, shared_state: None
) -> None:
    # A Module's `code` is executed as JavaScript in every session's browser,
    # so no session's browser may rewrite it through an ordinary `update`
    # comm message (the guard is installed at construction, before the
    # deferred open gives the widget a comm). `status` must still get
    # through: ipyreact's frontend reports module load progress with it.
    with session_context(widget_session):
        mod = ipyreact.define_module("shinywidgets_test_mod5", code="export default 1")
    assert getattr(mod, "_shinywidgets_ipyreact_guarded", False)
    from tests.unit.test_shared_widgets import flush

    flush()
    poison = {
        "header": {"msg_id": "poison-ipyreact", "msg_type": "comm_msg"},
        "content": {
            "comm_id": mod.model_id,
            "data": {
                "method": "update",
                "state": {"code": "window.pwned = true", "status": "Loaded module!"},
                "buffer_paths": [],
            },
        },
        "buffers": [],
    }
    with session_context(widget_session):
        sw.handle_client_comm_msg(widget_session, poison)
    assert mod.code == "export default 1"
    assert mod.status == "Loaded module!"


def test_init_session_adoption_installs_guard(
    ipyreact: Any,
    widget_session: Session,
    shared_state: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Simulate a Module that predates our construction hook (ipyreact
    # imported before shinywidgets): nothing guarded it or registered it in
    # SHARED_WIDGETS. The adoption in init_session() must guard it before
    # opening it in the session.
    real_guards = sw._STATE_GUARDS
    monkeypatch.setattr(sw, "_STATE_GUARDS", ())
    mod = ipyreact.define_module("shinywidgets_test_mod6", code="export default 1")
    monkeypatch.setattr(sw, "_STATE_GUARDS", real_guards)
    assert not getattr(mod, "_shinywidgets_ipyreact_guarded", False)
    sw.SHARED_WIDGETS.pop(mod.model_id, None)
    sw.SHARED_WIDGETS.pop(mod.layout.model_id, None)

    with session_context(widget_session):
        sw.init_session(widget_session)
    assert getattr(mod, "_shinywidgets_ipyreact_guarded", False)
    from shinywidgets._comm import SharedShinyComm

    assert isinstance(mod.comm, SharedShinyComm)


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
