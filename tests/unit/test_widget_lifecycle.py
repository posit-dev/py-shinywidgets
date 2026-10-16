from __future__ import annotations

import asyncio
from typing import cast

import pytest
from ipywidgets import HTML
from shiny import Session, reactive
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets import session_lifetime
from shinywidgets._lifecycle import get_lifecycle
from shinywidgets._render_widget_base import WidgetRenderContext, render_widget_base


def test_explicit_close_cancels_pending_open(widget_session: Session) -> None:
    with session_context(widget_session):
        widget = HTML(value="pending")
        model_id = widget.model_id
        widget.close()
        asyncio.run(reactive.flush())
        lifecycle = get_lifecycle(widget_session)
    assert model_id not in lifecycle.comm_manager.comms
    assert model_id not in lifecycle.records
    assert lifecycle.snapshot().pending_initializers == 0


def test_session_lifetime_overrides_render(widget_session: Session) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                temporary = HTML(value="temporary")
                temporary_id = temporary.model_id
                with session_lifetime():
                    retained = HTML(value="retained")
                    retained_id = retained.model_id
        asyncio.run(reactive.flush())
        context.invalidate()
        asyncio.run(reactive.flush())
    assert temporary_id not in lifecycle.records
    assert retained_id in lifecycle.records
    assert retained_id in lifecycle.comm_manager.comms


def test_session_lifetime_requires_active_session() -> None:
    with pytest.raises(RuntimeError, match="requires an active Shiny session"):
        with session_lifetime():
            pass


def test_nested_session_lifetime_shares_one_lifetime(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        with session_lifetime():
            with session_lifetime():
                widget = HTML(value="nested")
    assert lifecycle.records[widget.model_id].lifetime is lifecycle.session_lifetime


def test_session_lifetime_restores_selection_on_exception(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                with pytest.raises(ValueError, match="boom"):
                    with session_lifetime():
                        raise ValueError("boom")
                temporary = HTML(value="temporary")
                temporary_id = temporary.model_id
        assert lifecycle.records[temporary_id].lifetime.kind == "render"
        asyncio.run(reactive.flush())
        context.invalidate()
        asyncio.run(reactive.flush())
    assert temporary_id not in lifecycle.records


def test_session_lifetime_restores_selection_on_cancellation(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                try:
                    with session_lifetime():
                        raise asyncio.CancelledError()
                except asyncio.CancelledError:
                    pass
                temporary = HTML(value="temporary")
                temporary_id = temporary.model_id
    assert lifecycle.records[temporary_id].lifetime.kind == "render"


def test_interleaved_renders_keep_separate_lifetimes(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        contexts: dict[str, Context] = {}
        model_ids: dict[str, str] = {}

        async def make(name: str, delay: float) -> None:
            renderer = render_widget_base()

            @renderer
            async def _() -> HTML:  # noqa: ANN202
                await asyncio.sleep(delay)
                return HTML(value=name)

            ctx = Context()
            contexts[name] = ctx
            with ctx():
                result = await renderer.render()
            assert isinstance(result, dict)
            model_ids[name] = cast(str, result["model_id"])

        async def main() -> None:
            await asyncio.gather(make("a", 0.02), make("b", 0.01))

        asyncio.run(main())
        asyncio.run(reactive.flush())

        record_a = lifecycle.records[model_ids["a"]]
        record_b = lifecycle.records[model_ids["b"]]
        assert record_a.lifetime is not record_b.lifetime
        assert record_a.lifetime.kind == "render"
        assert record_b.lifetime.kind == "render"

        contexts["a"].invalidate()
        asyncio.run(reactive.flush())

        assert model_ids["a"] not in lifecycle.records
        assert model_ids["b"] in lifecycle.records


def test_session_lifetime_does_not_adopt_existing_widgets(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                temporary = HTML(value="temporary")
                temporary_id = temporary.model_id
                with session_lifetime():
                    # Referencing/assigning an existing widget inside the block
                    # does not transfer it to the session lifetime.
                    alias = temporary  # noqa: F841
        asyncio.run(reactive.flush())
        context.invalidate()
        asyncio.run(reactive.flush())
    assert temporary_id not in lifecycle.records


def test_module_scoped_construction_uses_root_session(
    widget_session: Session,
) -> None:
    scoped = widget_session.make_scope("mod")
    with session_context(scoped):
        lifecycle = get_lifecycle(widget_session)
        with session_lifetime():
            widget = HTML(value="module")
    record = lifecycle.records[widget.model_id]
    assert record.lifetime is lifecycle.session_lifetime
    assert record.lifetime.session_id == widget_session.id


def test_session_lifetime_is_noop_for_stub_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import shinywidgets._lifecycle as lc

    from tests.unit._fakes import FakeSession

    stub = FakeSession(stub=True)
    monkeypatch.setattr(lc, "get_current_session", lambda: stub)

    def no_lifecycle(_session: object) -> object:
        raise AssertionError("stub sessions must not allocate a lifecycle")

    monkeypatch.setattr(lc, "get_lifecycle", no_lifecycle)
    # The Express discovery pass executes the same app source before a real
    # session exists; the declaration must be a no-op there.
    with lc.session_lifetime():
        pass


def test_session_end_before_pending_open(widget_session: Session) -> None:
    with session_context(widget_session):
        widget = HTML(value="doomed")
        model_id = widget.model_id
        lifecycle = get_lifecycle(widget_session)
        asyncio.run(widget_session.close())
        asyncio.run(reactive.flush())
    assert model_id not in lifecycle.records
    assert model_id not in lifecycle.comm_manager.comms
    assert lifecycle.snapshot().pending_initializers == 0


def test_render_retirement_closes_open_widget(widget_session: Session) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                widget = HTML(value="temporary")
                model_id = widget.model_id
        asyncio.run(reactive.flush())
        assert model_id in lifecycle.comm_manager.comms
        context.invalidate()
        asyncio.run(reactive.flush())
    assert model_id not in lifecycle.records
    assert model_id not in lifecycle.comm_manager.comms
    assert widget.comm is not None  # inert orphaned comm preserves the model ID
    assert widget.model_id == model_id
