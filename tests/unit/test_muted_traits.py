from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, Iterator, List, Sequence

import ipywidgets
import pytest
import shinywidgets._shinywidgets as sw
from shiny import App, Session, reactive, ui
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
    assert mute_requests_in(flush_to_browser()) == [
        {"shinywidgets": "mute", "traits": ["value"]}
    ]
    assert mute_requests_in(flush_b()) == [{"shinywidgets": "mute", "traits": ["min"]}]
