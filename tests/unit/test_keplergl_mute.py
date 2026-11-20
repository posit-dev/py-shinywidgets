from __future__ import annotations

import pytest
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_keplergl

from tests.unit.test_muted_traits import Flush, mute_requests_for, render_once

keplergl = pytest.importorskip("keplergl")


def test_config_trait_is_muted_without_the_accessor(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        m = keplergl.KeplerGl()
    render_once(render_keplergl(), m, widget_session)
    assert {"shinywidgets": "mute", "traits": ["config"]} in mute_requests_for(
        flush_to_browser(), m
    )


def test_config_trait_flows_with_the_accessor(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        m = keplergl.KeplerGl()
    render_once(render_keplergl(listen_to=["config"]), m, widget_session)
    assert mute_requests_for(flush_to_browser(), m) == [
        {"shinywidgets": "mute", "traits": []}
    ]


def test_config_accessor_seeds_and_follows_the_trait(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        m = keplergl.KeplerGl(config={"mapStyle": {"styleType": "dark"}})
    # rate_delay=0: the accessor debounces by default, and this test's sets
    # must publish synchronously (no running loop to schedule a timer on)
    r = render_keplergl(listen_to=["config"], rate_delay=0)
    render_once(r, m, widget_session)
    with session_context(widget_session):
        assert r.config() == {"mapStyle": {"styleType": "dark"}}
        m.config = {"mapStyle": {"styleType": "light"}}
        assert r.config() == {"mapStyle": {"styleType": "light"}}


def test_config_read_without_the_opt_in_raises(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        m = keplergl.KeplerGl()
    r = render_keplergl()
    render_once(r, m, widget_session)
    with pytest.raises(RuntimeError, match=r'listen_to=\["config"\]'):
        r.config()
