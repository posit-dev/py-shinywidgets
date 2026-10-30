import asyncio

import pytest
import shinywidgets._accessors as acc
import shinywidgets._render_widget_base as rwb
from shiny import reactive as shiny_reactive
from shiny.reactive._core import Context


class FakeLiveWidget:
    """Stands in for a widget whose comm is open."""

    comm = object()


class FakeContext:
    def __init__(self) -> None:
        self.invalidated = 0
        self._on_invalidate: list[object] = []

    def invalidate(self) -> None:
        self.invalidated += 1

    def on_invalidate(self, fn):  # type: ignore[no-untyped-def]
        self._on_invalidate.append(fn)
        return fn

    def run_invalidate_callbacks(self) -> None:
        for fn in list(self._on_invalidate):
            fn()


def test_value_and_widget_are_read_only() -> None:
    r = rwb.render_widget_base()

    with pytest.raises(RuntimeError, match=r"`value` attribute .* read only"):
        r.value = 1  # type: ignore[misc]

    with pytest.raises(RuntimeError, match=r"`widget` attribute .* read only"):
        r.widget = object()  # type: ignore[misc]


def test_value_access_before_render_in_reactive_context_invokes_req(
    monkeypatch,
) -> None:
    r = rwb.render_widget_base()
    ctx = FakeContext()

    monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)

    class _Sentinel(Exception):
        pass

    def _req(x):  # type: ignore[no-untyped-def]
        raise _Sentinel(x)

    monkeypatch.setattr(rwb, "req", _req)

    with pytest.raises(_Sentinel):
        _ = r.value


def test_value_access_outside_reactive_context_returns_none(monkeypatch) -> None:
    r = rwb.render_widget_base()
    monkeypatch.setattr(
        rwb, "get_current_context", lambda: (_ for _ in ()).throw(RuntimeError())
    )
    assert r.value is None


def test_value_read_registers_current_context(monkeypatch) -> None:
    r = rwb.render_widget_base()
    ctx = FakeContext()
    monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)

    r._value = object()  # pre-render state
    _ = r.value

    assert ctx in r._contexts


def test_contexts_invalidated_on_rerender(monkeypatch) -> None:
    r = rwb.render_widget_base()
    ctx = FakeContext()

    state = {"val": 1}

    @r
    async def _():  # noqa: ANN202
        return state["val"]

    # Avoid real widget conversions; non-DOMWidget path returns None.
    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())

    asyncio.run(r._render())

    monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)
    assert r.value == 1
    assert ctx in r._contexts

    state["val"] = 2
    asyncio.run(r._render())

    assert ctx.invalidated == 1


def test_render_returns_none_when_value_is_none() -> None:
    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        return None

    assert asyncio.run(r._render()) is None


def test_render_returns_none_when_widget_is_not_domwidget(monkeypatch) -> None:
    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        return object()

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())
    assert asyncio.run(r._render()) is None


def test_render_of_unsupported_builtin_raises_helpful_type_error() -> None:
    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        return "not a widget"

    with pytest.raises(TypeError, match="Don't know how to coerce"):
        asyncio.run(r._render())


def test_render_includes_widget_package_for_domwidgets(monkeypatch) -> None:
    class FakeDOMWidget(FakeLiveWidget):
        def __init__(self) -> None:
            self.model_id = "widget-1"

    widget = FakeDOMWidget()
    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        return widget

    monkeypatch.setattr(rwb, "DOMWidget", FakeDOMWidget)
    monkeypatch.setattr(rwb, "as_widget", lambda value: widget)
    monkeypatch.setattr(rwb, "set_layout_defaults", lambda w: (w, True))
    monkeypatch.setattr(rwb, "widget_pkg", lambda w: "plotly")

    assert asyncio.run(r._render()) == {
        "model_id": "widget-1",
        "fill": True,
        "widget_pkg": "plotly",
    }


def test_widget_render_context_records_the_render(monkeypatch) -> None:
    ctx = FakeContext()
    monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)

    assert rwb.WidgetRenderContext.is_rendering_widget() is False
    with rwb.WidgetRenderContext():
        assert rwb.WidgetRenderContext.is_rendering_widget() is True
        assert rwb.WidgetRenderContext.get_render_context() is ctx
    assert rwb.WidgetRenderContext.is_rendering_widget() is False


def test_widget_render_context_restores_an_enclosing_render(monkeypatch) -> None:
    outer, inner = FakeContext(), FakeContext()

    monkeypatch.setattr(rwb, "get_current_context", lambda: outer)
    with rwb.WidgetRenderContext():
        monkeypatch.setattr(rwb, "get_current_context", lambda: inner)
        with rwb.WidgetRenderContext():
            assert rwb.WidgetRenderContext.get_render_context() is inner
        assert rwb.WidgetRenderContext.get_render_context() is outer


def test_widget_render_context_get_render_context_raises_outside() -> None:
    with pytest.raises(RuntimeError, match="Not currently rendering a widget"):
        rwb.WidgetRenderContext.get_render_context()


def test_interleaved_renders_each_see_their_own_context(monkeypatch) -> None:
    # Shiny can run a session's outputs as concurrent tasks. Each render must see its
    # own Context after an `await`, even when another render started meanwhile.
    contexts = {"a": FakeContext(), "b": FakeContext()}
    current = {"ctx": None}
    monkeypatch.setattr(rwb, "get_current_context", lambda: current["ctx"])
    seen: dict[str, object] = {}

    async def render(name: str, delay: float) -> None:
        current["ctx"] = contexts[name]
        with rwb.WidgetRenderContext():
            await asyncio.sleep(delay)
            seen[name] = rwb.WidgetRenderContext.get_render_context()

    async def main() -> None:
        await asyncio.gather(render("a", 0.01), render("b", 0.02))
        assert rwb.WidgetRenderContext.is_rendering_widget() is False

    asyncio.run(main())
    assert seen == {"a": contexts["a"], "b": contexts["b"]}


def test_task_started_during_a_render_still_shares_its_context_after_it_exits(
    monkeypatch,
) -> None:
    # A task started during a render keeps a copy of the render's Context
    # (asyncio.create_task() snapshots the current contextvars). A
    # widget that task builds *after* the render body returns must still be
    # tied to that Context, or it leaks until the session ends instead of
    # closing when the render is eventually invalidated.
    monkeypatch.setattr(rwb, "get_current_context", lambda: FakeContext())
    seen: list[bool] = []

    async def main() -> None:
        release = asyncio.Event()

        async def later() -> None:
            seen.append(rwb.WidgetRenderContext.is_rendering_widget())
            await release.wait()
            seen.append(rwb.WidgetRenderContext.is_rendering_widget())

        with rwb.WidgetRenderContext():
            task = asyncio.create_task(later())
            await asyncio.sleep(0)
        release.set()
        await task

    asyncio.run(main())
    assert seen == [True, True]


def test_render_wraps_in_widget_render_context_and_restores_on_error(
    monkeypatch,
) -> None:
    ctx = FakeContext()
    monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)

    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        return 1

    class _Boom(Exception):
        pass

    async def _render_boom():  # type: ignore[no-untyped-def]
        assert rwb.WidgetRenderContext.is_rendering_widget() is True
        assert rwb.WidgetRenderContext.get_render_context() is ctx
        raise _Boom()

    monkeypatch.setattr(r, "_render", _render_boom)

    with pytest.raises(_Boom):
        asyncio.run(r.render())

    assert rwb.WidgetRenderContext.is_rendering_widget() is False


class RecordingAttach:
    def __init__(self) -> None:
        self.widgets: list[object] = []
        self.emit = None

    def __call__(self, widget, emit):  # type: ignore[no-untyped-def]
        self.widgets.append(widget)
        self.emit = emit
        return lambda: None


def renderer_with_clicked(att: RecordingAttach):  # type: ignore[no-untyped-def]
    class R(rwb.render_widget_base):
        accessor_specs = (
            acc.AccessorSpec(name="clicked", kind="event", attach=att, eager=True),
        )

        def clicked(self):  # type: ignore[no-untyped-def]
            return self._read_accessor("clicked")

    return R()


def test_rate_kwargs_are_stored_and_default_none() -> None:
    r = rwb.render_widget_base()
    assert r.rate_policy is None and r.rate_delay is None
    r2 = rwb.render_widget_base(rate_policy="throttle", rate_delay=100)
    assert r2.rate_policy == "throttle" and r2.rate_delay == 100


def test_render_attaches_accessors_to_the_coerced_widget(monkeypatch) -> None:
    att = RecordingAttach()
    r = renderer_with_clicked(att)
    widget = FakeLiveWidget()

    @r
    async def _():  # noqa: ANN202
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: widget)
    asyncio.run(r._render())
    assert att.widgets == [widget]
    assert r.clicked() is None
    att.emit({"x": 1})
    assert r.clicked() == {"x": 1}


def test_accessor_read_registers_current_context(monkeypatch) -> None:
    att = RecordingAttach()
    r = renderer_with_clicked(att)

    @r
    async def _():  # noqa: ANN202
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())
    asyncio.run(r._render())
    ctx = FakeContext()
    monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)
    with shiny_reactive.isolate():
        r.clicked()
    assert ctx in r._contexts


def test_render_returning_none_cancels_accessor_reads(monkeypatch) -> None:
    att = RecordingAttach()
    r = renderer_with_clicked(att)
    state = {"val": 1}

    @r
    async def _():  # noqa: ANN202
        return state["val"]

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())
    asyncio.run(r._render())
    att.emit({"x": 1})
    state["val"] = None
    asyncio.run(r._render())

    class Cancel(Exception):
        pass

    def cancel(*args):  # type: ignore[no-untyped-def]
        raise Cancel()

    monkeypatch.setattr(acc, "req", cancel)
    with pytest.raises(Cancel):
        r.clicked()


def test_render_registers_rate_policy_for_its_widget(monkeypatch) -> None:
    widget = FakeLiveWidget()
    r = rwb.render_widget_base(rate_policy="throttle")

    @r
    async def _():  # noqa: ANN202
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: widget)
    asyncio.run(r._render())
    rate = acc.rate_policy_for(widget)  # type: ignore[arg-type]
    assert rate is not None and (rate.policy, rate.delay_ms) == ("throttle", 250)


def test_reading_an_accessor_in_its_own_render_raises(monkeypatch) -> None:
    att = RecordingAttach()
    r = renderer_with_clicked(att)

    @r
    async def _():  # noqa: ANN202
        r.clicked()
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())
    with pytest.raises(RuntimeError, match="own render function"):
        asyncio.run(r._render())


def test_invalidated_reader_contexts_are_forgotten(monkeypatch) -> None:
    r = rwb.render_widget_base()
    ctx = FakeContext()
    monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)
    r._register_current_context()
    assert ctx in r._contexts
    ctx.run_invalidate_callbacks()
    assert ctx not in r._contexts


def test_rerender_invalidates_real_contexts_that_unregister_themselves(
    monkeypatch,
) -> None:
    # A real Context runs its on_invalidate callbacks (which drop it from
    # _contexts) synchronously inside invalidate()
    r = rwb.render_widget_base()
    contexts = [Context(), Context()]

    @r
    async def _():  # noqa: ANN202
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())
    asyncio.run(r._render())

    for ctx in contexts:
        monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)
        _ = r.value

    asyncio.run(r._render())

    assert all(ctx._invalidated for ctx in contexts)
    assert r._contexts == set()
