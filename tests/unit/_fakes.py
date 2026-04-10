from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class FakeContext:
    def __init__(self) -> None:
        self.invalidated = False
        self._on_invalidate: List[Callable[[], None]] = []

    def invalidate(self) -> None:
        self.invalidated = True

    def on_invalidate(self, fn: Callable[[], None]) -> None:
        self._on_invalidate.append(fn)

    def run_on_invalidate(self) -> None:
        for fn in list(self._on_invalidate):
            fn()


class FakeDependencyHandler:
    def __init__(self) -> None:
        self.mounts: List[Dict[str, Any]] = []

    def mount(self, path: str, app: Any, *, name: str) -> None:
        self.mounts.append({"path": path, "app": app, "name": name})


@dataclass
class FakeApp:
    lib_prefix: str = "/_lib"
    _dependency_handler: FakeDependencyHandler = field(default_factory=FakeDependencyHandler)


class FakeInput:
    def __init__(self) -> None:
        self._shinywidgets_comm_send_value: str = json.dumps(
            {"content": {"comm_id": "missing"}}
        )

    def shinywidgets_comm_send(self) -> str:
        return self._shinywidgets_comm_send_value


class FakeSession:
    def __init__(
        self,
        *,
        session_id: str = "s1",
        stub: bool = False,
        root: "FakeSession | None" = None,
    ) -> None:
        self.id = session_id
        self._stub = stub
        self.input = FakeInput()
        self.app = FakeApp()

        self._ended_handlers: List[Callable[[], None]] = []
        self._flush_handlers: List[Callable[[], Any]] = []
        self._flushed_handlers: List[Callable[[], Any]] = []

        # Used by init_shiny_widget() to embed deps into comm-open metadata.
        self._process_ui_calls: List[Any] = []

        self._root = root

    def is_stub_session(self) -> bool:
        return self._stub

    def root_scope(self) -> "FakeSession":
        return self._root if self._root is not None else self

    def on_ended(self, fn: Callable[[], None]) -> None:
        self._ended_handlers.append(fn)

    def end(self) -> None:
        for fn in list(self._ended_handlers):
            fn()

    def on_flush(self, fn: Callable[[], Any]) -> None:
        self._flush_handlers.append(fn)

    def on_flushed(self, fn: Callable[[], Any]) -> None:
        self._flushed_handlers.append(fn)

    async def send_custom_message(self, msg_type: str, msg_txt: str) -> None:
        # Unit tests inspect scheduled callbacks; they do not need to execute sends.
        return None

    def _process_ui(self, x: Any) -> Dict[str, Any]:
        self._process_ui_calls.append(x)
        return {"deps": ["dep1"]}


class FakeStaticFiles:
    def __init__(self, *, directory: str) -> None:
        self.directory = directory


class FakeCommManager:
    def __init__(self) -> None:
        self.comms: Dict[str, Any] = {}
        self.registered: List[str] = []
        self.unregistered: List[str] = []

    def register_comm(self, comm: Any) -> str:
        self.comms[comm.comm_id] = comm
        self.registered.append(comm.comm_id)
        return comm.comm_id

    def unregister_comm(self, comm: Any) -> Any:
        self.unregistered.append(comm.comm_id)
        return self.comms.pop(comm.comm_id)


class FakeShinyComm:
    def __init__(
        self,
        *,
        comm_id: str,
        comm_manager: Any,
        target_name: str,
        data: Optional[Dict[str, object]] = None,
        metadata: Optional[Dict[str, object]] = None,
        buffers: Optional[List[bytes]] = None,
        **keys: object,
    ) -> None:
        self.comm_id = comm_id
        self.comm_manager = comm_manager
        self.target_name = target_name
        self.data = data
        self.metadata = metadata
        self.buffers = buffers
        self.keys = keys
        self.last_msg: Optional[Dict[str, object]] = None
        self.comm_manager.register_comm(self)

    def handle_msg(self, msg: Dict[str, object]) -> None:
        self.last_msg = msg


class FakeEffect:
    def __init__(self, fn: Callable[[], Any], *, priority: Optional[int] = None) -> None:
        self.fn = fn
        self.priority = priority
        self.destroyed = False

    def destroy(self) -> None:
        self.destroyed = True

    def __call__(self) -> Any:
        return self.fn()


class FakeReactive:
    def __init__(self) -> None:
        self.effects: List[FakeEffect] = []

    def event(self, _trigger: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return deco

    def effect(
        self, fn: Optional[Callable[..., Any]] = None, *, priority: Optional[int] = None
    ) -> Any:
        def deco(f: Callable[..., Any]) -> FakeEffect:
            # Keep a reference to the underlying function for introspection in tests.
            eff = FakeEffect(f, priority=priority)
            self.effects.append(eff)
            return eff

        if fn is None:
            return deco
        return deco(fn)


class FakeWidget:
    def __init__(self) -> None:
        self._model_id: Optional[str] = None
        self.comm: Any = None
        self.closed = False
        self.calls: List[str] = []

    def _repr_mimebundle_(self) -> None:
        self.calls.append("_repr_mimebundle_")

    def get_state(self) -> Dict[str, Any]:
        self.calls.append("get_state")
        return {"x": 1}

    def close(self) -> None:
        self.closed = True
        # Mimic ipywidgets behavior: closing clears comm.
        self.comm = None
        self.calls.append("close")

    def has_trait(self, name: str) -> bool:
        return name in {"value", "x", "a", "b"}

    def observe(self, fn: Any, names: Any, type: Any) -> None:
        self.calls.append(f"observe:{names}:{type}")
        self._observed = (fn, names, type)

    def unobserve(self, fn: Any, names: Any, type: Any) -> None:
        self.calls.append(f"unobserve:{names}:{type}")
        self._unobserved = (fn, names, type)

