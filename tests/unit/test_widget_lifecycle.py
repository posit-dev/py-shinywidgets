from __future__ import annotations

import asyncio
import gc
import weakref
from typing import cast

import pytest
from ipywidgets import HTML
from shiny import App, Session, reactive, ui
from shiny._connection import MockConnection
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


def test_retirement_cancels_pending_open(widget_session: Session) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                widget = HTML(value="temporary")
                model_id = widget.model_id
        # Retire the render before its deferred initialization ever ran.
        context.invalidate()
        asyncio.run(reactive.flush())
    assert model_id not in lifecycle.records
    assert model_id not in lifecycle.comm_manager.comms
    assert lifecycle.snapshot().pending_initializers == 0


def test_external_close_removes_record(widget_session: Session) -> None:
    with session_context(widget_session):
        widget = HTML(value="temporary")
        model_id = widget.model_id
        lifecycle = get_lifecycle(widget_session)
        asyncio.run(reactive.flush())
        assert model_id in lifecycle.comm_manager.comms
        widget.close()
        asyncio.run(reactive.flush())
    assert model_id not in lifecycle.records
    assert model_id not in lifecycle.comm_manager.comms
    # Closing an already-closed record is a no-op.
    lifecycle.close_record(model_id)
    assert model_id not in lifecycle.records


def test_retired_widget_redisplay_raises(widget_session: Session) -> None:
    with session_context(widget_session):
        context = Context()
        with context():
            with WidgetRenderContext():
                widget = HTML(value="temporary")
        context.invalidate()

        renderer = render_widget_base()

        @renderer
        async def _() -> HTML:  # noqa: ANN202
            return widget

        redisplay_context = Context()
        with redisplay_context():
            with pytest.raises(RuntimeError, match="render lifetime has ended"):
                asyncio.run(renderer.render())


def test_explicitly_closed_widget_redisplay_raises(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        with session_lifetime():
            widget = HTML(value="retained")
        asyncio.run(reactive.flush())
        widget.close()

        renderer = render_widget_base()

        @renderer
        async def _() -> HTML:  # noqa: ANN202
            return widget

        redisplay_context = Context()
        with redisplay_context():
            with pytest.raises(RuntimeError, match="has been closed"):
                asyncio.run(renderer.render())


def test_cross_session_widget_rejected(widget_session: Session) -> None:
    other_app = App(ui.page_fluid(), lambda input, output, session: None)
    other_session = other_app._create_session(MockConnection())
    try:
        with session_context(widget_session):
            with session_lifetime():
                widget = HTML(value="retained")

        renderer = render_widget_base()

        @renderer
        async def _() -> HTML:  # noqa: ANN202
            return widget

        other_context = Context()
        with session_context(other_session):
            with other_context():
                with pytest.raises(RuntimeError, match="different Shiny session"):
                    asyncio.run(renderer.render())
    finally:
        asyncio.run(other_session.close())


def test_closed_metadata_does_not_retain_widget(widget_session: Session) -> None:
    with session_context(widget_session):
        widget = HTML(value="released")
        asyncio.run(reactive.flush())
        reference = weakref.ref(widget)
        widget.close()
        del widget
        gc.collect()
    assert reference() is None


def test_session_end_removes_lifecycle(widget_session: Session) -> None:
    import shinywidgets._lifecycle as lc

    with session_context(widget_session):
        HTML(value="x")
        get_lifecycle(widget_session)
    asyncio.run(widget_session.close())
    assert widget_session not in lc._lifecycles


def test_model_ids_are_session_namespaced(widget_session: Session) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        widget = HTML(value="x")
        namespace = lifecycle.epoch.model_namespace
        assert (
            widget.model_id
            == f"sw-{namespace}-{widget.model_id.removeprefix(f'sw-{namespace}-')}"
        )
        assert widget.model_id.startswith(f"sw-{namespace}-")
        # A full ID in the same namespace is accepted opaquely.
        same = lifecycle.qualify_model_id(widget.model_id)
        assert same == widget.model_id
        # A full ID from another namespace is rejected.
        with pytest.raises(RuntimeError, match="different session namespace"):
            lifecycle.qualify_model_id("sw-othernamespace-abc")


def test_envelope_round_trip_and_legacy_rejection(widget_session: Session) -> None:
    from shinywidgets._comm import pack_envelope, unpack_envelope

    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        msg = {"content": {"comm_id": "c1", "data": {"x": 1}}, "buffers": []}
        packet = pack_envelope(lifecycle.epoch, msg)
        assert packet["sw"] == 1
        assert unpack_envelope(lifecycle.epoch, packet) is msg

        with pytest.raises(RuntimeError, match="legacy shinywidgets packet"):
            unpack_envelope(lifecycle.epoch, {"content": {"comm_id": "c1"}})
        with pytest.raises(RuntimeError, match="different session/epoch"):
            unpack_envelope(
                lifecycle.epoch,
                {
                    "sw": 1,
                    "session_id": lifecycle.epoch.session_id,
                    "model_namespace": lifecycle.epoch.model_namespace,
                    "epoch_id": "some-other-epoch",
                    "msg": msg,
                },
            )
        with pytest.raises(RuntimeError, match="Malformed shinywidgets packet"):
            unpack_envelope(
                lifecycle.epoch,
                {
                    "sw": 1,
                    "session_id": lifecycle.epoch.session_id,
                    "model_namespace": lifecycle.epoch.model_namespace,
                    "epoch_id": lifecycle.epoch.epoch_id,
                },
            )


def test_publication_transitions_release_unclaimed_provisional_lease(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        lifecycle = get_lifecycle(widget_session)
        first = lifecycle.publish("out", "gen-1", "root-1")
        assert lifecycle.snapshot().display_leases == 1
        # Publishing a newer value releases the unclaimed provisional lease.
        second = lifecycle.publish("out", "gen-2", "root-2")
        assert second.offer_id != first.offer_id
        assert first.provisional_lease_id not in lifecycle.display_leases
        assert second.provisional_lease_id in lifecycle.display_leases
        # A claimed lease is kept until its presentation release.
        claimed = lifecycle.display_leases[second.provisional_lease_id]
        claimed.mount_id = "mount-1"
        claimed.claim_seq = 1
        third = lifecycle.publish("out", "gen-3", "root-3")
        assert second.provisional_lease_id in lifecycle.display_leases
        # Null/error publication invalidates the offer.
        lifecycle.retract("out")
        assert "out" not in lifecycle.publications
        assert third.provisional_lease_id not in lifecycle.display_leases
        assert second.provisional_lease_id in lifecycle.display_leases
        lifecycle.release_display(second.provisional_lease_id)
        assert lifecycle.snapshot().display_leases == 0


def test_module_render_publishes_through_root_session(
    widget_session: Session,
) -> None:
    scoped = widget_session.make_scope("mod")
    with session_context(scoped):
        lifecycle = get_lifecycle(widget_session)
        context = Context()
        with context():
            with WidgetRenderContext():
                widget = HTML(value="module")
                model_id = widget.model_id

        renderer = render_widget_base()

        @renderer
        async def out() -> HTML:  # noqa: ANN202
            return widget

        render_context = Context()
        with render_context():
            result = asyncio.run(renderer.render())

    assert isinstance(result, dict)
    # The renderer's local output_id is resolved with the module's namespace.
    assert result["output_id"] == "mod-out"
    publication = lifecycle.publications["mod-out"]
    assert publication.root_id == model_id
    assert result["offer_id"] == publication.offer_id
    assert result["candidate_lease_id"] == publication.provisional_lease_id
