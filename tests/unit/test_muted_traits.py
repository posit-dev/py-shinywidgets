from __future__ import annotations

import asyncio
import gc
import json
from typing import Any, Callable, Dict, Iterator, List, Sequence

import ipywidgets
import pytest
import shinywidgets._shinywidgets as sw
from shiny import App, Session, reactive, req, ui
from shiny._connection import MockConnection
from shiny.session import session_context
from shinywidgets import render_widget
from shinywidgets._comm import SharedShinyComm

from tests.unit.conftest import widget_test_server

Flush = Callable[[], List[Dict[str, Any]]]


class render_muting(render_widget[ipywidgets.IntSlider]):
    """A renderer that mutes the slider's `value`, for testing the plumbing."""

    def _muted_traits(self, widget: ipywidgets.IntSlider) -> Sequence[str]:
        return ["value"]


def mute_requests(
    widget_session: Session, flush: Flush, renderer: render_widget[Any]
) -> List[Dict[str, Any]]:
    @renderer
    def _() -> ipywidgets.IntSlider:
        return ipywidgets.IntSlider()

    with session_context(widget_session):
        asyncio.get_event_loop().run_until_complete(renderer._render())
    return mute_requests_in(flush())


def mute_requests_in(sent: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    custom = [
        m["content"]["data"]["content"]
        for m in sent
        if m["type"] == "shinywidgets_comm_msg"
        and m["content"]["data"].get("method") == "custom"
    ]
    return [c for c in custom if c.get("shinywidgets") == "mute"]


def test_render_asks_the_browser_to_mute_the_traits_a_renderer_names(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    requests = mute_requests(widget_session, flush_to_browser, render_muting())
    assert requests == [{"shinywidgets": "mute", "traits": ["value"]}]


def test_renderers_state_an_empty_muted_set_by_default(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    # The whole set is sent on every render (even an empty one), so a reused
    # widget's previous set is cleared
    assert mute_requests(widget_session, flush_to_browser, render_widget()) == [
        {"shinywidgets": "mute", "traits": []}
    ]


@pytest.mark.parametrize("value", ["1", "true", "TRUE"])
def test_native_events_env_var_turns_muting_off(
    widget_session: Session,
    flush_to_browser: Flush,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("SHINYWIDGETS_NATIVE_EVENTS", value)
    assert mute_requests(widget_session, flush_to_browser, render_muting()) == [
        {"shinywidgets": "mute", "traits": []}
    ]


@pytest.mark.parametrize("value", ["", "0", "false", "no"])
def test_native_events_env_var_off_values_still_mute(
    widget_session: Session,
    flush_to_browser: Flush,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("SHINYWIDGETS_NATIVE_EVENTS", value)
    requests = mute_requests(widget_session, flush_to_browser, render_muting())
    assert requests == [{"shinywidgets": "mute", "traits": ["value"]}]


class render_muting_switchable(render_widget[ipywidgets.IntSlider]):
    """A renderer whose muted set the test flips between renders."""

    muted: List[str] = ["value"]

    def _muted_traits(self, widget: ipywidgets.IntSlider) -> Sequence[str]:
        return self.muted


class render_muting_min(render_widget[ipywidgets.IntSlider]):
    def _muted_traits(self, widget: ipywidgets.IntSlider) -> Sequence[str]:
        return ["min"]


def test_rerender_clears_a_reused_widgets_muted_set(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        w = ipywidgets.IntSlider()

    renderer = render_muting_switchable()

    @renderer
    def _() -> ipywidgets.IntSlider:
        # Reused across renders (e.g. cached via session_lifetime())
        return w

    def render() -> None:
        with session_context(widget_session):
            asyncio.get_event_loop().run_until_complete(renderer._render())

    renderer.muted = ["value"]
    render()
    first = mute_requests_in(flush_to_browser())
    assert first == [{"shinywidgets": "mute", "traits": ["value"]}]

    # The set becoming empty must reach the browser as an explicit clear,
    # not be skipped (leaving ["value"] muted there)
    renderer.muted = []
    render()
    assert mute_requests_in(flush_to_browser())[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }


@pytest.fixture
def other_session() -> Iterator[Session]:
    session = App(ui.page_fluid(), widget_test_server)._create_session(MockConnection())
    try:
        yield session
    finally:
        asyncio.get_event_loop().run_until_complete(session.close())


def session_recorder(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> Callable[[], List[Dict[str, Any]]]:
    """A flush_to_browser-style recorder for a session other than the fixture's."""
    sent: List[Dict[str, Any]] = []

    async def record(msg_type: str, msg_txt: str) -> None:
        if msg_type.startswith("shinywidgets_comm_"):
            sent.append({"type": msg_type, **json.loads(msg_txt)})

    monkeypatch.setattr(session, "send_custom_message", record)

    def flush() -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        with session_context(session):
            loop.run_until_complete(reactive.flush())
            loop.run_until_complete(session._flush_callbacks.invoke())
            loop.run_until_complete(session._flushed_callbacks.invoke())
        return sent

    return flush


def test_mute_policy_reaches_only_the_rendering_session(
    widget_session: Session,
    flush_to_browser: Flush,
    other_session: Session,
    shared_state: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a, b = widget_session, other_session
    flush_b = session_recorder(b, monkeypatch)

    # A process-global widget: its comm fans send() out to EVERY session, so
    # this is the case a mute policy must not leak across
    with session_context(a), sw.shared_construction():
        w = ipywidgets.IntSlider()
    flush_to_browser()

    def render(renderer: render_widget[Any], session: Session) -> None:
        @renderer
        def _() -> ipywidgets.IntSlider:
            return w

        with session_context(session):
            asyncio.get_event_loop().run_until_complete(renderer._render())

    # b renders first, wrapping w.comm into a SharedShinyComm over both sessions
    render(render_muting_min(), b)
    assert isinstance(w.comm, SharedShinyComm)
    render(render_muting(), a)
    flush_to_browser()
    flush_b()

    # Each session's browser got only its own renderer's policy: with the
    # fan-out send, both would have received both
    assert mute_requests_for(flush_to_browser(), w) == [
        {"shinywidgets": "mute", "traits": ["value"]}
    ]
    assert mute_requests_for(flush_b(), w) == [
        {"shinywidgets": "mute", "traits": ["min"]}
    ]


# ---------------------------------------------------------------------------
# Per-output mute policies: outputs in one session showing the same widget
# must not fight over the browser's per-model muted set (which every mute
# message replaces wholesale)
# ---------------------------------------------------------------------------


class render_muting_value_min(render_widget[ipywidgets.IntSlider]):
    def _muted_traits(self, widget: ipywidgets.IntSlider) -> Sequence[str]:
        return ["value", "min"]


def render_once(renderer: render_widget[Any], widget: Any, session: Session) -> None:
    @renderer
    def _() -> Any:
        return widget

    rerender(renderer, session)


def rerender(renderer: render_widget[Any], session: Session) -> None:
    with session_context(session):
        asyncio.get_event_loop().run_until_complete(renderer._render())


def mute_requests_for(
    sent: List[Dict[str, Any]], widget: ipywidgets.Widget
) -> List[Dict[str, Any]]:
    """The mute requests in `sent` addressed to `widget`'s model."""
    return [
        m["content"]["data"]["content"]
        for m in sent
        if m["type"] == "shinywidgets_comm_msg"
        and m["content"].get("comm_id") == widget.model_id
        and m["content"]["data"].get("method") == "custom"
        and m["content"]["data"]["content"].get("shinywidgets") == "mute"
    ]


def test_outputs_sharing_a_widget_mute_only_what_they_all_mute(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        w = ipywidgets.IntSlider()

    # The muting render comes first; the unmuted one must not inherit it
    # (both renderers are held, so neither policy retires mid-test)
    muting, unmuted = render_muting(), render_widget()
    render_once(muting, w, widget_session)
    render_once(unmuted, w, widget_session)
    assert mute_requests_in(flush_to_browser())[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }


def test_mute_intersection_does_not_depend_on_render_order(
    widget_session: Session,  # for its event loop and CDN-only monkeypatch
    other_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flush = session_recorder(other_session, monkeypatch)
    with session_context(other_session):
        w = ipywidgets.IntSlider()

    # The muting render comes last: a per-render send would leave ["value"]
    # muted for the output that needs it (the browser keeps the last set)
    unmuted, muting = render_widget(), render_muting()
    render_once(unmuted, w, other_session)
    render_once(muting, w, other_session)
    assert mute_requests_in(flush())[-1] == {"shinywidgets": "mute", "traits": []}


def test_shared_widget_mute_set_is_the_intersection(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        w = ipywidgets.IntSlider()

    value_min, value = render_muting_value_min(), render_muting()
    render_once(value_min, w, widget_session)
    render_once(value, w, widget_session)
    assert mute_requests_in(flush_to_browser())[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }


def test_rerender_with_a_different_widget_reverts_the_old_models_set(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        old, new = ipywidgets.IntSlider(), ipywidgets.IntSlider()

    current = [old]
    renderer = render_muting()

    @renderer
    def _() -> ipywidgets.IntSlider:
        return current[0]

    rerender(renderer, widget_session)
    assert mute_requests_for(flush_to_browser(), old) == [
        {"shinywidgets": "mute", "traits": ["value"]}
    ]

    # The render switches widgets: its policy moves off `old`, whose browser
    # is told explicitly (a model's set is only ever replaced, never cleared)
    current[0] = new
    rerender(renderer, widget_session)
    sent = flush_to_browser()
    assert mute_requests_for(sent, old)[-1] == {"shinywidgets": "mute", "traits": []}
    assert mute_requests_for(sent, new)[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }


def test_a_dropped_renderers_policy_no_longer_shapes_the_mute_set(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        w = ipywidgets.IntSlider()

    unmuted = render_widget()
    muting = render_muting()
    render_once(unmuted, w, widget_session)
    render_once(muting, w, widget_session)

    # The unmuted output suppresses the other's policy (intersection)
    assert mute_requests_in(flush_to_browser())[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }

    session_id = widget_session.root_scope().id
    consumers = sw._MUTE_POLICIES[session_id][str(w.model_id)]
    assert set(consumers) == {unmuted, muting}

    # The unmuted output retires: its policy leaves the registry, so the
    # muting output's next render mutes again
    del unmuted
    gc.collect()
    assert set(consumers) == {muting}

    rerender(muting, widget_session)
    assert mute_requests_for(flush_to_browser(), w)[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }


def test_surviving_outputs_rerender_stays_unmuted_after_the_muting_one_retires(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        w = ipywidgets.IntSlider()

    muting = render_muting()
    unmuted = render_widget()
    render_once(muting, w, widget_session)
    render_once(unmuted, w, widget_session)

    del muting
    gc.collect()

    rerender(unmuted, widget_session)
    assert mute_requests_in(flush_to_browser())[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }


def test_unrender_retires_the_outputs_mute_policy(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        w = ipywidgets.IntSlider()

    muting = render_muting()
    render_once(muting, w, widget_session)

    current: List[Any] = [w]
    unmuted = render_widget()

    @unmuted
    def _() -> Any:
        return current[0]

    rerender(unmuted, widget_session)

    # Both outputs show w: the intersection is empty
    assert mute_requests_in(flush_to_browser())[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }

    # The unmuted output un-renders: its policy retires, and the drop
    # re-sends w's set, now the muting output's policy alone
    current[0] = None
    rerender(unmuted, widget_session)
    assert mute_requests_for(flush_to_browser(), w)[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }

    # The muting output's next render mutes effectively
    rerender(muting, widget_session)
    assert mute_requests_for(flush_to_browser(), w)[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }


def test_a_failed_replacement_render_retires_the_mute_policy(
    widget_session: Session,
    flush_to_browser: Flush,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session_context(widget_session):
        w = ipywidgets.IntSlider()

    muting = render_muting()
    render_once(muting, w, widget_session)
    assert mute_requests_in(flush_to_browser())[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }

    # The re-render fails in coercion: no replacement widget exists for the
    # output, so its policy retires (clearing w's set) rather than keep
    # muting a model the output no longer shows
    class _Boom(Exception):
        pass

    def fail(value: Any) -> Any:
        raise _Boom()

    import shinywidgets._render_widget_base as rwb

    monkeypatch.setattr(rwb, "as_widget", fail)
    with pytest.raises(_Boom):
        rerender(muting, widget_session)

    assert mute_requests_for(flush_to_browser(), w)[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }
    assert widget_session.root_scope().id not in sw._MUTE_POLICIES


def test_a_render_function_error_retires_the_mute_policy(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        w = ipywidgets.IntSlider()

    muting = render_muting()
    render_once(muting, w, widget_session)

    class _Boom(Exception):
        pass

    fail = [False]
    unmuted = render_widget()

    @unmuted
    def _() -> ipywidgets.IntSlider:
        if fail[0]:
            raise _Boom()
        return w

    rerender(unmuted, widget_session)

    # Both outputs show w: the intersection is empty
    assert mute_requests_in(flush_to_browser())[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }

    # The unmuted output's render function fails: the output shows an error
    # instead of w, so its policy retires, and the drop re-sends w's set,
    # now the muting output's policy alone
    fail[0] = True
    with pytest.raises(_Boom):
        rerender(unmuted, widget_session)
    assert mute_requests_for(flush_to_browser(), w)[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }

    # The muting output's next render mutes effectively
    rerender(muting, widget_session)
    assert mute_requests_for(flush_to_browser(), w)[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }


def test_a_cancelled_render_keeps_the_mute_policy(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    from shiny.types import SilentCancelOutputException

    with session_context(widget_session):
        w = ipywidgets.IntSlider()

    cancel = [False]
    muting = render_muting()

    @muting
    def _() -> ipywidgets.IntSlider:
        if cancel[0]:
            # Keeps the output's previous view (the browser is sent
            # nothing), unlike a plain req(False), which clears it
            req(False, cancel_output=True)
        return w

    rerender(muting, widget_session)
    session_id = widget_session.root_scope().id
    assert muting in sw._MUTE_POLICIES[session_id][str(w.model_id)]

    # The view (and so the policy's reason to exist) survives the
    # cancellation, so the policy stays registered and nothing is re-sent
    cancel[0] = True
    with pytest.raises(SilentCancelOutputException):
        rerender(muting, widget_session)
    assert muting in sw._MUTE_POLICIES[session_id][str(w.model_id)]


# ---------------------------------------------------------------------------
# Container renders: an output showing a container also shows every widget
# reachable from it, so the consumer registers (an empty policy) for each
# reachable model, not just the container's own
# ---------------------------------------------------------------------------


def test_a_container_render_unmutes_a_child_another_output_mutes(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        slider = ipywidgets.IntSlider()
        box = ipywidgets.VBox(children=[slider])

    muting, container = render_muting(), render_widget()

    # The muting output renders the slider directly, first
    render_once(muting, slider, widget_session)
    assert mute_requests_for(flush_to_browser(), slider)[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }

    # The container output shows the slider too: its (empty) policy joins the
    # slider model's consumers, so the intersection un-mutes the slider in
    # both views
    render_once(container, box, widget_session)
    assert mute_requests_for(flush_to_browser(), slider)[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }


def test_a_container_render_unmutes_a_child_another_output_mutes_reversed(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        slider = ipywidgets.IntSlider()
        box = ipywidgets.VBox(children=[slider])

    container, muting = render_widget(), render_muting()

    # The container render comes first; the muting output's direct render of
    # the slider must still leave the model unmuted (the browser keeps the
    # last set it heard)
    render_once(container, box, widget_session)
    render_once(muting, slider, widget_session)
    assert mute_requests_for(flush_to_browser(), slider)[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }


def test_leaving_a_container_retires_its_child_model_registrations(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        slider = ipywidgets.IntSlider()
        box = ipywidgets.VBox(children=[slider])
        other = ipywidgets.IntSlider()

    muting = render_muting()
    render_once(muting, slider, widget_session)

    current: List[Any] = [box]
    container = render_widget()

    @container
    def _() -> Any:
        return current[0]

    rerender(container, widget_session)

    session_id = widget_session.root_scope().id
    models = sw._MUTE_POLICIES[session_id]
    # The container's empty policy is registered on its own model and the
    # slider's alike
    assert container in models[str(box.model_id)]
    assert container in models[str(slider.model_id)]

    # Switching widgets moves every registration off the old tree, and the
    # slider model's set reverts to the direct output's policy
    current[0] = other
    rerender(container, widget_session)
    models = sw._MUTE_POLICIES[session_id]
    assert container not in models.get(str(box.model_id), {})
    assert container not in models.get(str(slider.model_id), {})
    assert container in models[str(other.model_id)]
    assert mute_requests_for(flush_to_browser(), slider)[-1] == {
        "shinywidgets": "mute",
        "traits": ["value"],
    }

    # Un-rendering retires the registrations the same way
    current[0] = None
    rerender(container, widget_session)
    assert container not in sw._MUTE_POLICY_MODELS
    models = sw._MUTE_POLICIES[session_id]
    assert container not in models.get(str(other.model_id), {})


def test_session_end_drops_the_sessions_mute_policies(
    widget_session: Session,  # for its event loop and CDN-only monkeypatch
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = App(ui.page_fluid(), widget_test_server)._create_session(MockConnection())

    async def noop(msg_type: str, msg_txt: str) -> None:
        pass

    monkeypatch.setattr(session, "send_custom_message", noop)

    with session_context(session):
        w = ipywidgets.IntSlider()
    render_once(render_muting(), w, session)

    session_id = session.root_scope().id
    assert session_id in sw._MUTE_POLICIES
    asyncio.get_event_loop().run_until_complete(session.close())
    assert session_id not in sw._MUTE_POLICIES
