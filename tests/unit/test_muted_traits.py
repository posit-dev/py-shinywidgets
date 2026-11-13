from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Sequence

import ipywidgets
import pytest
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_widget

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
    custom = [
        m["content"]["data"]["content"]
        for m in flush()
        if m["type"] == "shinywidgets_comm_msg"
        and m["content"]["data"].get("method") == "custom"
    ]
    return [c for c in custom if c.get("shinywidgets") == "mute"]


def test_render_asks_the_browser_to_mute_the_traits_a_renderer_names(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    requests = mute_requests(widget_session, flush_to_browser, render_muting())
    assert requests == [{"shinywidgets": "mute", "traits": ["value"]}]


def test_renderers_mute_nothing_by_default(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    assert mute_requests(widget_session, flush_to_browser, render_widget()) == []


@pytest.mark.parametrize("value", ["1", "true", "TRUE"])
def test_native_events_env_var_turns_muting_off(
    widget_session: Session,
    flush_to_browser: Flush,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("SHINYWIDGETS_NATIVE_EVENTS", value)
    assert mute_requests(widget_session, flush_to_browser, render_muting()) == []


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
