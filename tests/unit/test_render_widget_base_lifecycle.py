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


class FakeSession:
    pass


def test_value_and_widget_are_read_only() -> None:
    r = rwb.render_widget_base()

    with pytest.raises(RuntimeError, match=r"`value` attribute .* read only"):
        r.value = 1  # type: ignore[misc]

    with pytest.raises(RuntimeError, match=r"`widget` attribute .* read only"):
        r.widget = object()  # type: ignore[misc]


def test_value_access_before_render_in_reactive_context_invokes_req(monkeypatch) -> None:
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
    monkeypatch.setattr(rwb, "get_current_context", lambda: (_ for _ in ()).throw(RuntimeError()))
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


def test_widget_render_context_restores_session_vars(monkeypatch) -> None:
    session = FakeSession()
    ctx = FakeContext()

    monkeypatch.setattr(rwb, "require_active_session", lambda _session: session)
    monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)

    vars(session)["__shinywidget_current_output_id"] = "old-id"
    vars(session)["__shinywidget_render_context"] = "old-ctx"

    with rwb.WidgetRenderContext("new-id"):
        assert vars(session)["__shinywidget_current_output_id"] == "new-id"
        assert vars(session)["__shinywidget_render_context"] is ctx
        assert rwb.WidgetRenderContext.is_rendering_widget(session) is True

    assert vars(session)["__shinywidget_current_output_id"] == "old-id"
    assert vars(session)["__shinywidget_render_context"] == "old-ctx"
    assert rwb.WidgetRenderContext.is_rendering_widget(session) is True  # old-id is not None


def test_widget_render_context_get_render_context_raises_outside() -> None:
    session = FakeSession()
    with pytest.raises(RuntimeError, match="Not currently rendering a widget"):
        rwb.WidgetRenderContext.get_render_context(session)


def test_render_wraps_in_widget_render_context_and_restores_on_error(monkeypatch) -> None:
    session = FakeSession()
    ctx = FakeContext()

    monkeypatch.setattr(rwb, "require_active_session", lambda _session: session)
    monkeypatch.setattr(rwb, "get_current_context", lambda: ctx)

    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        return 1

    vars(session)["__shinywidget_current_output_id"] = "old-id"
    vars(session)["__shinywidget_render_context"] = "old-ctx"

    class _Boom(Exception):
        pass

    async def _render_boom():  # type: ignore[no-untyped-def]
        assert rwb.WidgetRenderContext.is_rendering_widget(session) is True
        assert rwb.WidgetRenderContext.get_render_context(session) is ctx
        raise _Boom()

    monkeypatch.setattr(r, "_render", _render_boom)

    with pytest.raises(_Boom):
        asyncio.run(r.render())

    assert vars(session)["__shinywidget_current_output_id"] == "old-id"
    assert vars(session)["__shinywidget_render_context"] == "old-ctx"

