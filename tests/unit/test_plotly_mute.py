from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Sequence

import plotly.graph_objects as go
import pytest
import shinywidgets._plotly as sp
import shinywidgets._shinywidgets as sw
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_plotly, render_widget
from shinywidgets._comm import SharedShinyComm

from tests.unit.test_muted_traits import (
    mute_requests_for,
    mute_requests_in,
    other_session,
    render_once,
    rerender,
    session_recorder,
)
from tests.unit.test_plotly_accessors import FakeFigureWidget

__all__ = ("other_session",)

MUTE = {"shinywidgets": "mute", "traits": ["_js2py_pointsCallback"]}
UNMUTED = {"shinywidgets": "mute", "traits": []}

Flush = Callable[[], List[Dict[str, Any]]]


def figure() -> go.FigureWidget:
    return go.FigureWidget(go.Scatter(x=[1, 2, 3], y=[1, 2, 3]))


def noop(*args: object) -> None:
    pass


def test_points_callback_trait_is_muted_without_native_callbacks(
    widget_session: Session,
) -> None:
    # plotly.py's widget syncs every click, hover and selection to Python
    # through this trait, per point, whether or not anything listens (#479)
    with session_context(widget_session):
        assert sp.muted_traits(figure()) == ["_js2py_pointsCallback"]


@pytest.mark.parametrize(
    "register",
    ["on_click", "on_hover", "on_unhover", "on_selection", "on_deselect"],
)
def test_native_callback_keeps_the_points_callback_trait(
    widget_session: Session, register: str
) -> None:
    with session_context(widget_session):
        fig = figure()
        getattr(fig.data[0], register)(noop)
        assert sp.muted_traits(fig) == []


def test_native_callback_on_any_trace_keeps_the_trait(widget_session: Session) -> None:
    with session_context(widget_session):
        fig = figure()
        fig.add_scatter(x=[1], y=[1])
        fig.data[1].on_click(noop)
        assert sp.muted_traits(fig) == []


def mute_requests(
    widget_session: Session,
    flush: Flush,
    build: Callable[[], go.FigureWidget],
    listen_to: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    """The mute requests the browser receives when `build()`'s figure renders."""
    r = render_plotly(listen_to=listen_to)

    @r
    def _() -> go.FigureWidget:
        return build()

    with session_context(widget_session):
        asyncio.get_event_loop().run_until_complete(r._render())
    return mute_requests_in(flush())


def test_render_asks_the_browser_to_mute(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    assert mute_requests(widget_session, flush_to_browser, figure) == [MUTE]


def test_render_with_native_callback_mutes_nothing(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    def build() -> go.FigureWidget:
        fig = figure()
        fig.data[0].on_selection(noop)
        return fig

    # The whole set is stated on every render (even an empty one), so a
    # reused figure's previously muted set is cleared
    assert mute_requests(widget_session, flush_to_browser, build) == [
        {"shinywidgets": "mute", "traits": []}
    ]


def test_listening_to_native_mutes_nothing(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    # For what a render can't see: callbacks registered later, and reads of
    # plotly.py's Python-side `selectedpoints`
    requests = mute_requests(
        widget_session, flush_to_browser, figure, listen_to=["native"]
    )
    assert requests == [{"shinywidgets": "mute", "traits": []}]


def test_native_is_listened_to_alongside_accessors() -> None:
    r = render_plotly(listen_to=["native", "selected"])
    r._accessors.on_render(FakeFigureWidget())
    assert r.selected() is None


def test_misspelled_native_is_rejected_and_names_it() -> None:
    with pytest.raises(ValueError, match="'native'"):
        render_plotly(listen_to=["nativ"])


def test_native_is_not_a_name_for_renderers_that_mute_nothing() -> None:
    with pytest.raises(ValueError, match="native"):
        render_widget(listen_to=["native"])


def test_rerender_restores_native_events_when_a_callback_is_registered(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        fig = figure()

    r = render_plotly()

    @r
    def _() -> go.FigureWidget:
        # Reused across renders (e.g. cached via session_lifetime())
        return fig

    def render() -> None:
        with session_context(widget_session):
            asyncio.get_event_loop().run_until_complete(r._render())

    render()
    assert mute_requests_in(flush_to_browser()) == [MUTE]

    # A callback registered after the first render unmutes on the next: the
    # empty set must reach the browser as an explicit clear, not be skipped
    # (leaving _js2py_pointsCallback muted there)
    fig.data[0].on_click(noop)
    render()
    assert mute_requests_in(flush_to_browser())[-1] == {
        "shinywidgets": "mute",
        "traits": [],
    }


def test_mute_policy_reaches_only_the_rendering_session(
    widget_session: Session,
    flush_to_browser: Flush,
    other_session: Session,
    shared_state: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a, b = widget_session, other_session
    flush_b = session_recorder(b, monkeypatch)

    # A shared FigureWidget: its comm fans send() out to EVERY session, so
    # this is the case a mute policy must not leak across
    with session_context(a), sw.shared_construction():
        fig = figure()
    flush_to_browser()

    def render(session: Session, listen_to: Sequence[str] = ()) -> None:
        r = render_plotly(listen_to=listen_to)

        @r
        def _() -> go.FigureWidget:
            return fig

        with session_context(session):
            asyncio.get_event_loop().run_until_complete(r._render())

    # b renders first, wrapping fig.comm into a SharedShinyComm over both sessions
    render(b)
    assert isinstance(fig.comm, SharedShinyComm)
    render(a, listen_to=["native"])
    flush_to_browser()
    flush_b()

    # Each session's browser got only its own render's policy: with the
    # fan-out send, b's default render would have muted a's native events
    # despite a's listen_to=["native"] opt-in
    assert mute_requests_in(flush_to_browser()) == [
        {"shinywidgets": "mute", "traits": []}
    ]
    assert mute_requests_in(flush_b()) == [MUTE]


# ---------------------------------------------------------------------------
# Outputs in one session sharing a FigureWidget: the browser keeps one
# (last-sent) muted set per model, so every render sends the intersection
# over the model's consumers -- and a consumer moving off the model restores
# what the remaining consumers mute
# ---------------------------------------------------------------------------


def test_default_then_native_render_leaves_native_events_unmuted(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        fig = figure()

    # Both renderers are held, so neither mute policy retires mid-test
    default, native = render_plotly(), render_plotly(listen_to=["native"])
    render_once(default, fig, widget_session)
    render_once(native, fig, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == UNMUTED


def test_native_then_default_render_leaves_native_events_unmuted(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        fig = figure()

    # The muting render comes last: a per-render send would leave
    # ["_js2py_pointsCallback"] muted for the output that opted into native
    # events (the browser keeps the last set it received)
    native, default = render_plotly(listen_to=["native"]), render_plotly()
    render_once(native, fig, widget_session)
    render_once(default, fig, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == UNMUTED


def test_a_generic_output_does_not_unregister_the_plotly_mute(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        fig, other = figure(), figure()

    plotly, generic = render_plotly(), render_widget()
    render_once(plotly, fig, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == MUTE

    # A generic render_widget mutes nothing, so while it shows fig the
    # intersection is empty -- the plotly output's policy is overlaid, not
    # dropped
    render_once(generic, fig, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == UNMUTED

    # ... so the generic output moving to another widget restores it
    render_once(generic, other, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == MUTE


def test_a_generic_output_does_not_unregister_the_plotly_mute_reverse_order(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        fig, other = figure(), figure()

    # The plotly render comes last: a per-render send would leave its
    # ["_js2py_pointsCallback"] in place for the generic output too
    generic, plotly = render_widget(), render_plotly()
    render_once(generic, fig, widget_session)
    render_once(plotly, fig, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == UNMUTED

    # The plotly output's policy outlives the generic output's stay on fig
    render_once(generic, other, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == MUTE


def test_a_failed_native_render_retires_its_policy(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        fig = figure()

    # The muting (default) output shows fig first
    default = render_plotly()
    render_once(default, fig, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == MUTE

    class _Boom(Exception):
        pass

    fail = [False]
    native = render_plotly(listen_to=["native"])

    @native
    def _() -> go.FigureWidget:
        if fail[0]:
            raise _Boom()
        return fig

    rerender(native, widget_session)

    # Both outputs show fig: the intersection is empty (the native output
    # opted into native events)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == UNMUTED

    # The native output's render function fails: the output shows an error
    # instead of fig, so its policy retires, and the drop re-sends fig's
    # set, now the default output's policy alone
    fail[0] = True
    with pytest.raises(_Boom):
        rerender(native, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == MUTE

    # The surviving default output's next render mutes effectively
    rerender(default, widget_session)
    assert mute_requests_for(flush_to_browser(), fig)[-1] == MUTE
