import pytest
import shinywidgets._shinywidgets as sw


class FakeContext:
    def __init__(self) -> None:
        self.invalidated = 0
        self._on_invalidate = []

    def invalidate(self) -> None:
        self.invalidated += 1

    def on_invalidate(self, fn):  # type: ignore[no-untyped-def]
        self._on_invalidate.append(fn)
        return fn

    def run_invalidate_callbacks(self) -> None:
        for fn in list(self._on_invalidate):
            fn()


class FakeWidget:
    def __init__(self, traits: dict[str, object]) -> None:
        self._traits = set(traits.keys())
        for k, v in traits.items():
            setattr(self, k, v)

        self.observe_calls = []
        self.unobserve_calls = []

    def has_trait(self, name: str) -> bool:
        return name in self._traits

    def observe(self, handler, names, type):  # type: ignore[no-untyped-def]
        self.observe_calls.append((handler, list(names), type))

    def unobserve(self, handler, names, type):  # type: ignore[no-untyped-def]
        self.unobserve_calls.append((handler, list(names), type))


def test_reactive_depend_outside_context_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        sw, "get_current_context", lambda: (_ for _ in ()).throw(RuntimeError())
    )
    w = FakeWidget({"x": 1})

    with pytest.raises(
        RuntimeError,
        match=r"reactive_read\(\) must be called within a reactive context",
    ):
        sw.reactive_depend(w, "x")  # type: ignore[arg-type]


def test_reactive_read_outside_context_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        sw, "get_current_context", lambda: (_ for _ in ()).throw(RuntimeError())
    )
    w = FakeWidget({"x": 1})

    with pytest.raises(
        RuntimeError,
        match=r"reactive_read\(\) must be called within a reactive context",
    ):
        sw.reactive_read(w, "x")  # type: ignore[arg-type]


def test_reactive_depend_validates_trait_existence(monkeypatch) -> None:
    ctx = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: ctx)
    w = FakeWidget({"ok": 1})

    with pytest.raises(ValueError) as excinfo:
        sw.reactive_depend(w, "nope")  # type: ignore[arg-type]

    msg = str(excinfo.value)
    assert "nope" in msg
    assert "FakeWidget" in msg


def test_reactive_depend_observe_and_cleanup_wiring(monkeypatch) -> None:
    ctx = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: ctx)
    w = FakeWidget({"a": 1, "b": 2})

    sw.reactive_depend(w, ["a", "b"], type="change")  # type: ignore[arg-type]

    assert len(w.observe_calls) == 1
    handler, names, typ = w.observe_calls[0]
    assert names == ["a", "b"]
    assert typ == "change"

    handler(change={})
    assert ctx.invalidated == 1

    ctx.run_invalidate_callbacks()

    assert len(w.unobserve_calls) == 1
    uhandler, unames, utyp = w.unobserve_calls[0]
    assert uhandler is handler
    assert unames == ["a", "b"]
    assert utyp == "change"


def test_reactive_read_returns_values_in_order(monkeypatch) -> None:
    ctx = FakeContext()
    monkeypatch.setattr(sw, "get_current_context", lambda: ctx)
    w = FakeWidget({"a": 1, "b": 2})

    assert sw.reactive_read(w, "a") == 1  # type: ignore[arg-type]
    assert sw.reactive_read(w, ["a", "b"]) == (1, 2)  # type: ignore[arg-type]
