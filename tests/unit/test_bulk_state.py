from __future__ import annotations

import base64
from typing import Any


class FakeBulkWidget:
    """Minimal widget stub for build_manager_state tests."""

    def __init__(
        self,
        model_id: str,
        state: dict[str, Any],
        *,
        model_name: str = "MyModel",
        model_module: str = "my_module",
        model_module_version: str = "1.0.0",
    ) -> None:
        self._model_id = model_id
        self._state = state
        self._model_name = model_name
        self._model_module = model_module
        self._model_module_version = model_module_version
        self.comm: Any = None

    @property
    def model_id(self) -> str:
        return self._model_id

    def get_state(self, drop_defaults: bool = False) -> dict[str, Any]:
        return dict(self._state)


# ---------------------------------------------------------------------------
# find_ipy_model_refs tests
# ---------------------------------------------------------------------------


def test_find_ipy_model_refs_empty_state():
    from shinywidgets._bulk_state import find_ipy_model_refs

    assert find_ipy_model_refs({}) == set()


def test_find_ipy_model_refs_flat():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"layout": "IPY_MODEL_abc123", "style": "IPY_MODEL_def456"}
    assert find_ipy_model_refs(state) == {"abc123", "def456"}


def test_find_ipy_model_refs_nested_dicts():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"outer": {"inner": "IPY_MODEL_nested1"}}
    assert find_ipy_model_refs(state) == {"nested1"}


def test_find_ipy_model_refs_lists():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"layers": ["IPY_MODEL_l1", "IPY_MODEL_l2", "not_a_ref"]}
    assert find_ipy_model_refs(state) == {"l1", "l2"}


def test_find_ipy_model_refs_mixed_nesting():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {
        "controls": [
            {"widget": "IPY_MODEL_ctrl1"},
            "IPY_MODEL_ctrl2",
        ],
        "name": "Map",
        "count": 42,
        "layout": "IPY_MODEL_lay1",
    }
    assert find_ipy_model_refs(state) == {"ctrl1", "ctrl2", "lay1"}


def test_find_ipy_model_refs_deduplicates():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"a": "IPY_MODEL_x", "b": "IPY_MODEL_x"}
    assert find_ipy_model_refs(state) == {"x"}


def test_find_ipy_model_refs_ignores_non_model_strings():
    from shinywidgets._bulk_state import find_ipy_model_refs

    state = {"label": "IPY_MODEL_looks_like_ref", "title": "not IPY_MODEL_nope", "prefix": "IPY_MODE"}
    # "IPY_MODEL_looks_like_ref" IS a ref (starts with IPY_MODEL_)
    # "not IPY_MODEL_nope" is NOT (doesn't start with prefix)
    # "IPY_MODE" is NOT (too short)
    assert find_ipy_model_refs(state) == {"looks_like_ref"}


# ---------------------------------------------------------------------------
# build_manager_state tests
# ---------------------------------------------------------------------------


def test_build_manager_state_single_widget():
    from shinywidgets._bulk_state import build_manager_state

    root = FakeBulkWidget("root1", {"x": 1})
    widget_map = {"root1": root}

    result = build_manager_state(
        root_widget=root,
        widget_instance_map=widget_map,
        remove_buffers=lambda state: (state, [], []),
        collect_deps=lambda w: [],
    )

    assert result["root_model_id"] == "root1"
    assert "root1" in result["state"]
    entry = result["state"]["root1"]
    assert entry["model_name"] == "MyModel"
    assert entry["model_module"] == "my_module"
    assert entry["model_module_version"] == "1.0.0"
    assert entry["state"] == {"x": 1}
    assert entry["buffers"] == []


def test_build_manager_state_traverses_children():
    from shinywidgets._bulk_state import build_manager_state

    child = FakeBulkWidget("child1", {"val": 42})
    root = FakeBulkWidget("root1", {"layer": "IPY_MODEL_child1"})
    widget_map = {"root1": root, "child1": child}

    result = build_manager_state(
        root_widget=root,
        widget_instance_map=widget_map,
        remove_buffers=lambda state: (state, [], []),
        collect_deps=lambda w: [],
    )

    assert "root1" in result["state"]
    assert "child1" in result["state"]


def test_build_manager_state_deep_graph():
    from shinywidgets._bulk_state import build_manager_state

    leaf = FakeBulkWidget("leaf", {"v": 0})
    mid = FakeBulkWidget("mid", {"child": "IPY_MODEL_leaf"})
    root = FakeBulkWidget("root", {"child": "IPY_MODEL_mid"})
    widget_map = {"root": root, "mid": mid, "leaf": leaf}

    result = build_manager_state(
        root_widget=root,
        widget_instance_map=widget_map,
        remove_buffers=lambda state: (state, [], []),
        collect_deps=lambda w: [],
    )

    assert set(result["state"].keys()) == {"root", "mid", "leaf"}


def test_build_manager_state_handles_buffers():
    from shinywidgets._bulk_state import build_manager_state

    root = FakeBulkWidget("root1", {"data": "some_data"})
    widget_map = {"root1": root}

    def fake_remove_buffers(state: dict[str, Any]) -> tuple[dict[str, Any], list[list[str]], list[bytes]]:
        return ({"data": None}, [["data"]], [b"\x00\x01\x02"])

    result = build_manager_state(
        root_widget=root,
        widget_instance_map=widget_map,
        remove_buffers=fake_remove_buffers,
        collect_deps=lambda w: [],
    )

    entry = result["state"]["root1"]
    assert entry["state"] == {"data": None}
    assert len(entry["buffers"]) == 1
    assert entry["buffers"][0]["path"] == ["data"]
    assert entry["buffers"][0]["encoding"] == "base64"
    assert base64.b64decode(entry["buffers"][0]["data"]) == b"\x00\x01\x02"


def test_build_manager_state_collects_and_deduplicates_deps():
    from shinywidgets._bulk_state import build_manager_state

    child = FakeBulkWidget("child", {"v": 0})
    root = FakeBulkWidget("root", {"c": "IPY_MODEL_child"})
    widget_map = {"root": root, "child": child}

    dep_a = {"name": "widgetA", "version": "1.0", "src": "/a"}
    dep_b = {"name": "widgetB", "version": "2.0", "src": "/b"}

    def fake_collect_deps(w: Any) -> list[dict[str, Any]]:
        if w.model_id == "root":
            return [dep_a, dep_b]
        return [dep_a]  # duplicate

    result = build_manager_state(
        root_widget=root,
        widget_instance_map=widget_map,
        remove_buffers=lambda state: (state, [], []),
        collect_deps=fake_collect_deps,
    )

    # dep_a appears once even though both widgets produce it.
    names = [d["name"] for d in result["html_deps"]]
    assert names.count("widgetA") == 1
    assert "widgetB" in names


def test_build_manager_state_skips_missing_references():
    from shinywidgets._bulk_state import build_manager_state

    root = FakeBulkWidget("root", {"layer": "IPY_MODEL_missing"})
    widget_map = {"root": root}

    result = build_manager_state(
        root_widget=root,
        widget_instance_map=widget_map,
        remove_buffers=lambda state: (state, [], []),
        collect_deps=lambda w: [],
    )

    # Only root is in the closure — missing ref is silently skipped.
    assert set(result["state"].keys()) == {"root"}


def test_build_manager_state_calls_repr_mimebundle():
    from shinywidgets._bulk_state import build_manager_state

    called: list[str] = []

    class MimeBundleWidget(FakeBulkWidget):
        def _repr_mimebundle_(self, **kwargs: Any) -> None:
            called.append(self.model_id)

    root = MimeBundleWidget("root", {"v": 1})
    widget_map = {"root": root}

    build_manager_state(
        root_widget=root,
        widget_instance_map=widget_map,
        remove_buffers=lambda state: (state, [], []),
        collect_deps=lambda w: [],
    )

    assert "root" in called


# ---------------------------------------------------------------------------
# materialize_bulk_comms tests
# ---------------------------------------------------------------------------


def test_materialize_bulk_comms_creates_comms_and_sets_flag():
    from shinywidgets._bulk_state import materialize_bulk_comms
    from tests.unit._fakes import FakeCommManager, FakeShinyComm

    w1 = FakeBulkWidget("w1", {"v": 1})
    w2 = FakeBulkWidget("w2", {"v": 2})
    widget_map: dict[str, Any] = {"w1": w1, "w2": w2}
    comm_mgr = FakeCommManager()

    state_entries = {
        "w1": {"state": {"v": 1}},
        "w2": {"state": {"v": 2}},
    }

    class _nullcontext:
        def __enter__(self):
            return self

        def __exit__(self, *a: object):
            return False

    materialize_bulk_comms(
        state_entries=state_entries,
        widget_instance_map=widget_map,
        comm_manager=comm_mgr,
        comm_class=FakeShinyComm,
        widget_comm_patch=lambda: _nullcontext(),
    )

    assert w1.comm is not None
    assert w1.comm.comm_id == "w1"
    assert w1.comm.target_name == "jupyter.widget"
    assert getattr(w1, "_shinywidgets_bulk_owned", False) is True
    assert "w1" in comm_mgr.comms
    assert getattr(w2, "_shinywidgets_bulk_owned", False) is True


def test_materialize_bulk_comms_skips_missing_widgets():
    from shinywidgets._bulk_state import materialize_bulk_comms
    from tests.unit._fakes import FakeCommManager, FakeShinyComm

    widget_map: dict[str, Any] = {}
    comm_mgr = FakeCommManager()

    class _nullcontext:
        def __enter__(self):
            return self

        def __exit__(self, *a: object):
            return False

    # Should not raise even though "gone" is not in widget_map
    materialize_bulk_comms(
        state_entries={"gone": {"state": {}}},
        widget_instance_map=widget_map,
        comm_manager=comm_mgr,
        comm_class=FakeShinyComm,
        widget_comm_patch=lambda: _nullcontext(),
    )

    assert len(comm_mgr.comms) == 0


# ---------------------------------------------------------------------------
# _open_shiny_comm bulk-owned guard test
# ---------------------------------------------------------------------------


def test_open_shiny_comm_skips_bulk_owned_widget(monkeypatch):
    """When _shinywidgets_bulk_owned is True, the scheduled open effect
    should self-destruct without creating a ShinyComm."""
    import shinywidgets._shinywidgets as sw
    from tests.unit._fakes import (
        FakeCommManager,
        FakeReactive,
        FakeSession,
        FakeShinyComm,
        FakeStaticFiles,
        FakeWidget,
    )

    class _nullcontext:
        def __enter__(self):
            return self

        def __exit__(self, *a: object):
            return False

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
    monkeypatch.setattr(sw, "SESSIONS", sw.WeakSet())
    monkeypatch.setattr(sw, "SESSION_WIDGET_ID_MAP", {})
    monkeypatch.setattr(sw, "WIDGET_INSTANCE_MAP", {})

    w = FakeWidget()
    # Simulate that the bulk path has already claimed this widget.
    w._shinywidgets_bulk_owned = True  # type: ignore[attr-defined]

    sw.init_shiny_widget(w)  # type: ignore[arg-type]

    open_eff = next(e for e in reactive.effects if e.fn.__name__ == "_open_shiny_comm")
    open_eff()

    # Effect self-destructed without creating a real comm.
    assert open_eff.destroyed is True
    # The comm should still be the OrphanedShinyComm assigned by init_shiny_widget
    # (not a FakeShinyComm from the open path).
    assert not isinstance(w.comm, FakeShinyComm)
