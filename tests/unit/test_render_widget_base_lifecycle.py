import asyncio

import pytest
import shinywidgets._render_widget_base as rwb


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
    monkeypatch.setattr(rwb, "as_widget", lambda value: object())

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

    monkeypatch.setattr(rwb, "as_widget", lambda value: object())
    assert asyncio.run(r._render()) is None


def test_render_includes_widget_package_for_domwidgets(monkeypatch) -> None:
    class FakeDOMWidget:
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


def test_task_started_during_a_render_is_not_rendering_after_it(monkeypatch) -> None:
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
    assert seen == [True, False]


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
