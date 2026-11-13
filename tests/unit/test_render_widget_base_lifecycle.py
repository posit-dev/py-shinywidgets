import asyncio
from typing import Any

import pytest
import shinywidgets._accessors as acc
import shinywidgets._render_widget_base as rwb
import shinywidgets._shinywidgets as sw
from shiny import reactive as shiny_reactive
from shiny.reactive._core import Context
from shiny.reactive._extended_task import DenialContext


class FakeLiveComm:
    """Stands in for an open ShinyComm (what a render's sends go through)."""

    def __init__(self) -> None:
        self.sent: list = []

    def send(self, data=None, metadata=None, buffers=None):  # type: ignore[no-untyped-def]
        self.sent.append(data)


class FakeLiveWidget:
    """Stands in for a widget whose comm is open."""

    model_id = "fake-live-widget"

    def __init__(self) -> None:
        self.comm = FakeLiveComm()

    def send(self, content, buffers=None):  # type: ignore[no-untyped-def]
        # ipywidgets' Widget.send(); every render sends its muted-traits
        # policy, even an empty one
        pass


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
            super().__init__()
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
        self.detached = 0

    def __call__(self, widget, emit):  # type: ignore[no-untyped-def]
        self.widgets.append(widget)
        self.emit = emit

        def detach() -> None:
            self.detached += 1

        return detach


def renderer_with_clicked(att: RecordingAttach, kind: str = "event"):  # type: ignore[no-untyped-def]
    class R(rwb.render_widget_base):
        _accessor_specs = (acc.AccessorSpec(name="clicked", kind=kind, attach=att),)  # type: ignore[arg-type]

        def clicked(self):  # type: ignore[no-untyped-def]
            return self._read_accessor("clicked")

    return R()


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


class ModuleScope:
    """A module's session: destroying it doesn't end the root session."""

    id = "module-scope"

    def __init__(self) -> None:
        self.on_destroy_fns: list = []

    def is_stub_session(self) -> bool:
        return False

    def root_scope(self) -> "ModuleScope":
        return self

    def on_ended(self, fn) -> None:  # type: ignore[no-untyped-def]
        pass

    def on_destroy(self, fn) -> None:  # type: ignore[no-untyped-def]
        self.on_destroy_fns.append(fn)

    def destroy(self) -> None:
        for fn in self.on_destroy_fns:
            fn()


def test_destroying_the_module_scope_detaches_accessors(monkeypatch) -> None:
    # A destroyed scope's reactive values raise when set, so a listener (or a
    # pending debounce) publishing after destroy() would error
    att = RecordingAttach()
    r = renderer_with_clicked(att)

    @r
    async def _():  # noqa: ANN202
        return 1

    scope = ModuleScope()
    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())
    monkeypatch.setattr(rwb, "get_current_session", lambda: scope)
    monkeypatch.setattr(sw, "foreign_or_closed_widget", lambda widget, root: None)
    monkeypatch.setattr(sw, "open_process_global_widgets", lambda widget, root: None)
    asyncio.run(r._render())
    scope.destroy()
    att.emit({"x": 1})
    with shiny_reactive.isolate():
        assert r._accessors.values["clicked"].get().raw is None


def test_accessor_read_does_not_depend_on_the_render(monkeypatch) -> None:
    # Accessor readers invalidate only via the accessor's own reactive.Value
    # (a new interaction, a changed re-seed, an event-kind reset), so they
    # must NOT register in _contexts, which _render() invalidates wholesale
    # on every re-render (.widget/.value reads still do -- reactive_read()
    # has to re-attach to the new widget)
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
    assert ctx not in r._contexts
    # .widget still takes the render dependency
    r.widget
    assert ctx in r._contexts


def test_kept_accessor_reader_is_not_rerun_by_rerenders(monkeypatch) -> None:
    # An effect that reads a kept accessor and feeds a derived (new) object
    # back into the same output's render must settle, not loop: a re-render
    # must not re-run the accessor's readers when its value didn't change
    # (reactive.Value dedupes only on identity, so each re-run would re-set
    # the value and re-render forever)
    att = RecordingAttach()
    r = renderer_with_clicked(att, kind="state")

    fed = shiny_reactive.Value(0.0)
    renders: list = []
    reads: list = []

    @r
    async def _():  # noqa: ANN202
        renders.append(fed())
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())

    @shiny_reactive.Effect
    async def _drive() -> None:
        await r.render()

    @shiny_reactive.Effect
    def _watch() -> None:
        val: Any = r.clicked()
        if val is None or len(reads) >= 10:  # the cap keeps a loop finite
            return
        reads.append(val)
        fed.set(float(val["x"]) * 1.0)  # a new object on every run

    async def main() -> None:
        await shiny_reactive.flush()
        assert renders == [0.0] and reads == []

        att.emit({"x": 1})
        await shiny_reactive.flush()

        # The click re-ran the reader once, its derived set re-rendered the
        # output once, and that re-render did NOT re-run the reader
        assert reads == [{"x": 1}]
        assert renders == [0.0, 1.0]

    asyncio.run(main())


class SeededWidget:
    """A widget whose current state the accessor attach reports at once."""

    comm = object()

    def __init__(self, current) -> None:  # type: ignore[no-untyped-def]
        self.current = current

    def send(self, content, buffers=None):  # type: ignore[no-untyped-def]
        # ipywidgets' Widget.send(); every render sends its muted-traits
        # policy, even an empty one
        pass


def test_reseeded_accessor_reader_reruns_only_when_the_seed_changes(
    monkeypatch,
) -> None:
    # A re-render re-seeds a state accessor from the new widget: a seed that
    # differs from the published value still re-runs readers (publish-driven),
    # while an identical seed no longer does (same as an ordinary input)
    widgets = [SeededWidget(5), SeededWidget(5), SeededWidget(6)]

    def attach(widget, emit):  # type: ignore[no-untyped-def]
        emit(widget.current)
        return lambda: None

    class R(rwb.render_widget_base):
        _accessor_specs = (acc.AccessorSpec(name="zoom", kind="state", attach=attach),)

        def zoom(self):  # type: ignore[no-untyped-def]
            return self._read_accessor("zoom")

    r = R()
    trigger = shiny_reactive.Value(0)

    @r
    async def _():  # noqa: ANN202
        return trigger()

    monkeypatch.setattr(rwb, "as_widget", lambda value: widgets[value])

    reads: list = []

    @shiny_reactive.Effect
    async def _drive() -> None:
        await r.render()

    @shiny_reactive.Effect
    def _watch() -> None:
        reads.append(r.zoom())

    async def main() -> None:
        await shiny_reactive.flush()
        assert reads == [5]

        trigger.set(1)  # re-render with an identical seed
        await shiny_reactive.flush()
        assert reads == [5]

        trigger.set(2)  # re-render with a changed seed
        await shiny_reactive.flush()
        assert reads == [5, 6]

    asyncio.run(main())


def test_unrender_does_not_rerun_kept_accessor_readers(monkeypatch) -> None:
    # When the render function returns None (the output un-renders), a kept
    # accessor's readers keep their last value instead of being re-run into
    # the req(False) a read would now raise
    att = RecordingAttach()
    r = renderer_with_clicked(att, kind="state")

    trigger: shiny_reactive.Value[Any] = shiny_reactive.Value(1)

    @r
    async def _():  # noqa: ANN202
        return trigger()

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())

    runs: list = []
    reads: list = []

    @shiny_reactive.Effect
    async def _drive() -> None:
        await r.render()

    @shiny_reactive.Effect
    def _watch() -> None:
        runs.append(1)
        reads.append(r.clicked())

    async def main() -> None:
        await shiny_reactive.flush()
        att.emit({"x": 1})
        await shiny_reactive.flush()
        assert reads == [None, {"x": 1}]

        trigger.set(None)  # the output un-renders
        await shiny_reactive.flush()

        # The reader was not woken by the un-render
        assert len(runs) == 2
        assert reads == [None, {"x": 1}]

    asyncio.run(main())


def test_reader_that_ran_before_the_first_render_is_woken_by_it(monkeypatch) -> None:
    # A reader that runs before the output's first render cancels. The render
    # must wake it even though the accessor publishes nothing at attach (a
    # click accessor has no seed), or the reader stays blank until an
    # interaction
    att = RecordingAttach()
    r = renderer_with_clicked(att, kind="state")

    @r
    async def _():  # noqa: ANN202
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())

    reads: list = []

    # Created (and so first run) before the effect that renders
    @shiny_reactive.Effect
    def _watch() -> None:
        reads.append(r.clicked())

    @shiny_reactive.Effect
    async def _drive() -> None:
        await r.render()

    async def main() -> None:
        await shiny_reactive.flush()
        assert reads == [None]

    asyncio.run(main())


class PickyWidget:
    """A widget an accessor may or may not support."""

    comm = object()

    def __init__(self, supported: bool) -> None:
        self.supported = supported

    def send(self, content, buffers=None):  # type: ignore[no-untyped-def]
        # ipywidgets' Widget.send(); every render sends its muted-traits
        # policy, even an empty one
        pass


def picky_renderer_and_reads(  # type: ignore[no-untyped-def]
    monkeypatch, widgets: list[PickyWidget]
):
    """
    A renderer whose `clicked()` attach raises for an unsupported widget, the
    value that picks which of `widgets` it renders, what a reactive reader of
    `clicked()` saw on each run, and the attach.
    """
    att = RecordingAttach()

    def attach(widget, emit):  # type: ignore[no-untyped-def]
        if not widget.supported:
            raise TypeError("unsupported layout")
        return att(widget, emit)

    class R(rwb.render_widget_base):
        _accessor_specs = (
            acc.AccessorSpec(name="clicked", kind="state", attach=attach),
        )

        def clicked(self):  # type: ignore[no-untyped-def]
            return self._read_accessor("clicked")

    r = R()
    which = shiny_reactive.Value(0)

    @r
    async def _():  # noqa: ANN202
        return which()

    monkeypatch.setattr(rwb, "as_widget", lambda value: widgets[value])

    reads: list = []

    @shiny_reactive.Effect
    async def _drive() -> None:
        await r.render()

    @shiny_reactive.Effect
    def _watch() -> None:
        try:
            reads.append(r.clicked())
        except TypeError as e:
            reads.append(str(e))

    return which, reads, att


def test_rerender_whose_attach_fails_reruns_readers_into_the_error(
    monkeypatch,
) -> None:
    # on_render() swallows an attach failure so the output still renders, and
    # leaves raising to the next read: existing readers must be woken into
    # that read, or they keep showing the previous widget's value
    which, reads, att = picky_renderer_and_reads(
        monkeypatch, [PickyWidget(True), PickyWidget(False)]
    )

    async def main() -> None:
        await shiny_reactive.flush()
        att.emit({"x": 1})
        await shiny_reactive.flush()
        assert reads == [None, {"x": 1}]

        which.set(1)  # re-render with a widget the accessor doesn't support
        await shiny_reactive.flush()
        assert reads == [None, {"x": 1}, "unsupported layout"]

    asyncio.run(main())


def test_reader_that_raised_on_a_failed_attach_recovers_on_rerender(
    monkeypatch,
) -> None:
    # A reader holding an attach error must re-run once a re-render attaches
    # fine, even though that attach publishes nothing
    which, reads, att = picky_renderer_and_reads(
        monkeypatch, [PickyWidget(False), PickyWidget(True)]
    )

    async def main() -> None:
        await shiny_reactive.flush()
        assert reads == ["unsupported layout"]

        which.set(1)  # re-render with a widget the accessor supports
        await shiny_reactive.flush()
        assert reads == ["unsupported layout", None]

    asyncio.run(main())


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


def test_failed_rerender_detaches_accessors_from_the_previous_widget(
    monkeypatch,
) -> None:
    # _render() replaces _value/_widget before coercion; if coercion then
    # fails, accessors must not keep watching (and reporting) the previous
    # widget's state
    att = RecordingAttach()
    r = renderer_with_clicked(att)

    @r
    async def _():  # noqa: ANN202
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())
    asyncio.run(r._render())
    att.emit({"x": 1})
    assert r.clicked() == {"x": 1}
    assert att.detached == 0

    class _Boom(Exception):
        pass

    def fail(value):  # type: ignore[no-untyped-def]
        raise _Boom()

    monkeypatch.setattr(rwb, "as_widget", fail)
    with pytest.raises(_Boom):
        asyncio.run(r._render())

    assert att.detached == 1

    # Reads cancel while the output has no rendered widget...
    class Cancel(Exception):
        pass

    def cancel(*args):  # type: ignore[no-untyped-def]
        raise Cancel()

    monkeypatch.setattr(acc, "req", cancel)
    with pytest.raises(Cancel):
        r.clicked()
    # ...and the old widget's events no longer reach the accessor
    att.emit({"x": 2})
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
    assert rate is not None and (rate.policy, rate.delay) == ("throttle", 0.25)


def test_rate_delay_alone_debounces_reactive_read(monkeypatch) -> None:
    widget = FakeLiveWidget()
    r = rwb.render_widget_base(rate_delay=0.5)

    @r
    async def _():  # noqa: ANN202
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: widget)
    asyncio.run(r._render())
    rate = acc.rate_policy_for(widget)  # type: ignore[arg-type]
    assert rate is not None and (rate.policy, rate.delay) == ("debounce", 0.5)


def test_no_rate_kwargs_leave_reactive_read_unlimited(monkeypatch) -> None:
    widget = FakeLiveWidget()
    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: widget)
    asyncio.run(r._render())
    assert acc.rate_policy_for(widget) is None  # type: ignore[arg-type]


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


def test_reading_value_in_its_own_render_raises(monkeypatch) -> None:
    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        r.value  # would return the previous render's stale value
        return 1

    monkeypatch.setattr(rwb, "as_widget", lambda value: FakeLiveWidget())
    with pytest.raises(RuntimeError, match="own render function"):
        asyncio.run(r._render())


def test_reading_widget_in_its_own_render_raises(monkeypatch) -> None:
    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        r.widget  # would return the previous render's stale widget
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


def test_widget_is_readable_inside_an_extended_task(monkeypatch) -> None:
    # An extended task's body runs under a context that refuses dependencies;
    # e.g. geolibre's blocking methods must be called (on `.widget`) from one
    r = rwb.render_widget_base()

    @r
    async def _():  # noqa: ANN202
        return 1

    widget = FakeLiveWidget()
    monkeypatch.setattr(rwb, "as_widget", lambda value: widget)
    asyncio.run(r._render())

    monkeypatch.setattr(rwb, "get_current_context", lambda: DenialContext())
    assert r.widget is widget
    assert r._contexts == set()
