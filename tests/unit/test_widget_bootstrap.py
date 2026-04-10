from __future__ import annotations

import base64
import json
from typing import Any, Dict

import pytest

from tests.unit._fakes import (
    FakeCommManager,
    FakeContext,
    FakeReactive,
    FakeSession,
    FakeShinyComm,
    FakeStaticFiles,
    FakeWidget,
)


class _nullcontext:
    def __enter__(self):  # noqa: D401
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def reset_shinywidgets_globals(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    import shinywidgets._shinywidgets as sw

    monkeypatch.setattr(sw, "SESSIONS", sw.WeakSet())
    monkeypatch.setattr(sw, "SESSION_WIDGET_ID_MAP", {})
    monkeypatch.setattr(sw, "WIDGET_INSTANCE_MAP", {})
    return {"sw": sw}


def test_init_requires_active_session(monkeypatch):
    import shinywidgets._shinywidgets as sw

    monkeypatch.setattr(sw, "get_current_session", lambda: None)
    with pytest.raises(RuntimeError, match="active Shiny session"):
        sw.init_shiny_widget(FakeWidget())  # type: ignore[arg-type]


def test_init_returns_early_for_stub_session(monkeypatch, reset_shinywidgets_globals):
    sw = reset_shinywidgets_globals["sw"]
    reactive = FakeReactive()

    session = FakeSession(stub=True)
    monkeypatch.setattr(sw, "get_current_session", lambda: session)
    monkeypatch.setattr(sw, "reactive", reactive)

    w = FakeWidget()
    sw.init_shiny_widget(w)  # type: ignore[arg-type]

    assert session not in sw.SESSIONS
    assert sw.SESSION_WIDGET_ID_MAP == {}
    assert reactive.effects == []
    assert session.app._dependency_handler.mounts == []


def test_session_is_wired_once_and_open_effect_assigns_comm(
    monkeypatch, reset_shinywidgets_globals
):
    sw = reset_shinywidgets_globals["sw"]
    reactive = FakeReactive()
    comm_mgr = FakeCommManager()
    root = FakeSession(session_id="root")

    monkeypatch.setattr(sw, "get_current_session", lambda: root)
    monkeypatch.setattr(sw, "reactive", reactive)
    monkeypatch.setattr(sw, "COMM_MANAGER", comm_mgr)
    monkeypatch.setattr(sw, "StaticFiles", FakeStaticFiles)
    monkeypatch.setattr(sw, "SHINYWIDGETS_CDN_ONLY", True)
    monkeypatch.setattr(sw, "uuid4", lambda: type("U", (), {"hex": "w1"})())
    monkeypatch.setattr(sw, "_remove_buffers", lambda state: (state, [], []))
    monkeypatch.setattr(sw, "widget_comm_patch", lambda: _nullcontext())
    monkeypatch.setattr(sw, "ShinyComm", FakeShinyComm)

    w1 = FakeWidget()
    sw.init_shiny_widget(w1)  # type: ignore[arg-type]

    # Session wiring ran.
    assert root in sw.SESSIONS
    assert any(m["path"] == "/dist/" for m in root.app._dependency_handler.mounts)
    assert len(root._ended_handlers) == 1

    # Widget got an id and an orphaned comm immediately.
    assert w1._model_id == "w1"
    assert getattr(w1.comm, "comm_id", None) == "w1"

    open_eff = next(e for e in reactive.effects if e.fn.__name__ == "_open_shiny_comm")
    assert open_eff.priority == 99999
    open_eff()
    assert open_eff.destroyed is True
    assert isinstance(w1.comm, FakeShinyComm)
    assert comm_mgr.comms["w1"] is w1.comm
    assert "_repr_mimebundle_" in w1.calls
    assert "get_state" in w1.calls

    # Second widget in same session should not re-wire session-level hooks/mounts.
    monkeypatch.setattr(sw, "uuid4", lambda: type("U", (), {"hex": "w2"})())
    w2 = FakeWidget()
    sw.init_shiny_widget(w2)  # type: ignore[arg-type]
    assert len(root.app._dependency_handler.mounts) == 1
    assert len(root._ended_handlers) == 1


def test_comm_send_handler_routes_to_existing_comm(
    monkeypatch, reset_shinywidgets_globals
):
    sw = reset_shinywidgets_globals["sw"]
    reactive = FakeReactive()
    comm_mgr = FakeCommManager()
    root = FakeSession(session_id="root")

    monkeypatch.setattr(sw, "get_current_session", lambda: root)
    monkeypatch.setattr(sw, "reactive", reactive)
    monkeypatch.setattr(sw, "COMM_MANAGER", comm_mgr)
    monkeypatch.setattr(sw, "StaticFiles", FakeStaticFiles)
    monkeypatch.setattr(sw, "SHINYWIDGETS_CDN_ONLY", True)
    monkeypatch.setattr(sw, "uuid4", lambda: type("U", (), {"hex": "w1"})())
    monkeypatch.setattr(sw, "_remove_buffers", lambda state: (state, [], []))
    monkeypatch.setattr(sw, "widget_comm_patch", lambda: _nullcontext())
    monkeypatch.setattr(sw, "ShinyComm", FakeShinyComm)

    w = FakeWidget()
    sw.init_shiny_widget(w)  # type: ignore[arg-type]
    open_eff = next(e for e in reactive.effects if e.fn.__name__ == "_open_shiny_comm")
    open_eff()

    send_eff = next(e for e in reactive.effects if e.fn.__name__ == "_")
    root.input._shinywidgets_comm_send_value = json.dumps(
        {"content": {"comm_id": "w1"}}
    )
    send_eff()

    assert comm_mgr.comms["w1"].last_msg == {"content": {"comm_id": "w1"}}


def test_session_end_cleanup_closes_widgets_and_clears_maps(
    monkeypatch, reset_shinywidgets_globals
):
    sw = reset_shinywidgets_globals["sw"]
    reactive = FakeReactive()
    comm_mgr = FakeCommManager()
    root = FakeSession(session_id="root")

    monkeypatch.setattr(sw, "get_current_session", lambda: root)
    monkeypatch.setattr(sw, "reactive", reactive)
    monkeypatch.setattr(sw, "COMM_MANAGER", comm_mgr)
    monkeypatch.setattr(sw, "StaticFiles", FakeStaticFiles)
    monkeypatch.setattr(sw, "SHINYWIDGETS_CDN_ONLY", True)
    monkeypatch.setattr(sw, "uuid4", lambda: type("U", (), {"hex": "w1"})())
    monkeypatch.setattr(sw, "_remove_buffers", lambda state: (state, [], []))
    monkeypatch.setattr(sw, "widget_comm_patch", lambda: _nullcontext())
    monkeypatch.setattr(sw, "ShinyComm", FakeShinyComm)

    w = FakeWidget()
    sw.WIDGET_INSTANCE_MAP["w1"] = w

    sw.init_shiny_widget(w)  # type: ignore[arg-type]
    assert root.id in sw.SESSION_WIDGET_ID_MAP
    assert root in sw.SESSIONS

    root.end()
    assert root not in sw.SESSIONS
    assert w.closed is True
    assert root.id not in sw.SESSION_WIDGET_ID_MAP


def test_render_context_invalidation_closes_widget_and_preserves_model_id(
    monkeypatch, reset_shinywidgets_globals
):
    sw = reset_shinywidgets_globals["sw"]
    reactive = FakeReactive()
    comm_mgr = FakeCommManager()
    root = FakeSession(session_id="root")
    ctx = FakeContext()

    monkeypatch.setattr(sw, "get_current_session", lambda: root)
    monkeypatch.setattr(sw, "reactive", reactive)
    monkeypatch.setattr(sw, "COMM_MANAGER", comm_mgr)
    monkeypatch.setattr(sw, "StaticFiles", FakeStaticFiles)
    monkeypatch.setattr(sw, "SHINYWIDGETS_CDN_ONLY", True)
    monkeypatch.setattr(sw, "uuid4", lambda: type("U", (), {"hex": "w1"})())
    monkeypatch.setattr(sw, "_remove_buffers", lambda state: (state, [], []))
    monkeypatch.setattr(sw, "widget_comm_patch", lambda: _nullcontext())
    monkeypatch.setattr(sw, "ShinyComm", FakeShinyComm)

    monkeypatch.setattr(
        sw.WidgetRenderContext, "is_rendering_widget", staticmethod(lambda _s: True)
    )
    monkeypatch.setattr(
        sw.WidgetRenderContext, "get_render_context", staticmethod(lambda _s: ctx)
    )
    monkeypatch.setattr(sw, "session_context", lambda _s: _nullcontext())

    w = FakeWidget()
    sw.WIDGET_INSTANCE_MAP["w1"] = w
    sw.init_shiny_widget(w)  # type: ignore[arg-type]

    ctx.run_on_invalidate()
    assert w.closed is True
    assert getattr(w.comm, "comm_id", None) == "w1"
    assert "w1" not in sw.WIDGET_INSTANCE_MAP


def test_nbextensions_mount_when_widget_dep_has_subdir(
    monkeypatch, reset_shinywidgets_globals
):
    sw = reset_shinywidgets_globals["sw"]
    reactive = FakeReactive()
    comm_mgr = FakeCommManager()
    root = FakeSession(session_id="root")

    class Dep:
        name = "somewidget"
        source = {"subdir": "/tmp/somewidget"}

    monkeypatch.setattr(sw, "get_current_session", lambda: root)
    monkeypatch.setattr(sw, "reactive", reactive)
    monkeypatch.setattr(sw, "COMM_MANAGER", comm_mgr)
    monkeypatch.setattr(sw, "StaticFiles", FakeStaticFiles)
    monkeypatch.setattr(sw, "uuid4", lambda: type("U", (), {"hex": "w1"})())
    monkeypatch.setattr(sw, "_remove_buffers", lambda state: (state, [], []))
    monkeypatch.setattr(sw, "widget_comm_patch", lambda: _nullcontext())
    monkeypatch.setattr(sw, "ShinyComm", FakeShinyComm)

    monkeypatch.setattr(sw, "SHINYWIDGETS_CDN_ONLY", False)
    monkeypatch.setattr(sw, "require_dependency", lambda w, session, warn: Dep())

    w = FakeWidget()
    sw.init_shiny_widget(w)  # type: ignore[arg-type]
    mounts = root.app._dependency_handler.mounts
    assert any(m["path"] == "/nbextensions/somewidget" for m in mounts)


def test_reactive_depend_registers_and_unregisters_on_invalidate(monkeypatch):
    import shinywidgets._shinywidgets as sw

    ctx = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: ctx)

    w = FakeWidget()
    sw.reactive_depend(w, "x")  # type: ignore[arg-type]
    assert any(c.startswith("observe:") for c in w.calls)

    ctx.run_on_invalidate()
    assert any(c.startswith("unobserve:") for c in w.calls)

    with pytest.raises(ValueError):
        sw.reactive_depend(w, "not_a_trait")  # type: ignore[arg-type]


def test_reactive_depend_requires_reactive_context(monkeypatch):
    import shinywidgets._shinywidgets as sw

    def boom():
        raise RuntimeError("no ctx")

    monkeypatch.setattr(sw, "get_current_context", boom)
    with pytest.raises(RuntimeError, match="within a reactive context"):
        sw.reactive_depend(FakeWidget(), "x")  # type: ignore[arg-type]


def test_reactive_read_returns_values_and_delegates_depend(monkeypatch):
    import shinywidgets._shinywidgets as sw

    seen = []
    monkeypatch.setattr(
        sw,
        "reactive_depend",
        lambda widget, names, type="change": seen.append((widget, names, type)),
    )

    class W:
        a = 1
        b = 2

    w = W()
    assert sw.reactive_read(w, "a") == 1
    assert sw.reactive_read(w, ["a", "b"]) == (1, 2)
    assert seen[0][1] == "a"
    assert seen[1][1] == ["a", "b"]


def test_decode_comm_buffers_decodes_base64_and_preserves_existing_buffers():
    import shinywidgets._shinywidgets as sw

    existing = memoryview(b"\x02\x03")
    msg = {
        "buffers": [
            base64.b64encode(b"\x00\x01").decode("ascii"),
            existing,
        ]
    }

    res = sw._decode_comm_buffers(msg)

    assert res is msg
    assert res["buffers"][0].tobytes() == b"\x00\x01"
    assert res["buffers"][1] is existing


def test_is_traitlet_instance_false_for_plain_object():
    import shinywidgets._shinywidgets as sw

    assert sw.is_traitlet_instance(object()) is False


def test_widget_comm_patch_simulated_traitlet_instance(monkeypatch):
    import shinywidgets._shinywidgets as sw

    class FakeInstance:
        def __init__(self) -> None:
            self.klass = "orig"

    fake_inst = FakeInstance()

    monkeypatch.setattr(sw, "is_traitlet_instance", lambda x: True)
    monkeypatch.setattr(sw.Widget, "comm", fake_inst, raising=False)

    with sw.widget_comm_patch():
        assert sw.Widget.comm.klass is object

    assert sw.Widget.comm.klass == "orig"


def test_widget_comm_patch_noop_when_comm_not_traitlet_instance(monkeypatch):
    import shinywidgets._shinywidgets as sw

    class FakeAny:
        def __init__(self) -> None:
            self.klass = "orig"

    fake_any = FakeAny()

    monkeypatch.setattr(sw, "is_traitlet_instance", lambda x: False)
    monkeypatch.setattr(sw.Widget, "comm", fake_any, raising=False)

    with sw.widget_comm_patch():
        assert sw.Widget.comm.klass == "orig"

    assert sw.Widget.comm.klass == "orig"


def test_register_widget_uses_session_output_decorator(monkeypatch):
    import shinywidgets._shinywidgets as sw

    # Avoid real shiny/renderer decorator work.
    monkeypatch.setattr(sw, "render_widget", lambda fn: fn)
    monkeypatch.setattr(sw, "as_widget", lambda x: x)
    monkeypatch.setattr(sw, "require_active_session", lambda s: s)

    seen = {"output_id": None, "called": False}

    class Sess:
        def output(self, *, id):
            seen["output_id"] = id

            def deco(fn):
                seen["called"] = True
                return fn

            return deco

    w = object()
    res = sw.register_widget("out1", w, session=Sess())  # type: ignore[arg-type]
    assert res is w
    assert seen["output_id"] == "out1"
    assert seen["called"] is True


def test_register_widget_without_session_uses_active_session(monkeypatch):
    import shinywidgets._shinywidgets as sw

    seen = {"output_id": None, "registered_fn": None}

    class Sess:
        def output(self, *, id):
            seen["output_id"] = id

            def deco(fn):
                seen["registered_fn"] = fn
                return fn

            return deco

    sess = Sess()
    monkeypatch.setattr(sw, "render_widget", lambda fn: fn)
    monkeypatch.setattr(sw, "as_widget", lambda x: x)
    monkeypatch.setattr(sw, "require_active_session", lambda s: sess)

    w = object()
    res = sw.register_widget("out2", w)  # type: ignore[arg-type]

    assert res is w
    assert seen["output_id"] == "out2"
    assert seen["registered_fn"] is not None
    assert seen["registered_fn"]() is w
