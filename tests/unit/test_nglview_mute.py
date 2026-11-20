from __future__ import annotations

import pytest
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_nglview

from tests.unit.test_muted_traits import Flush, mute_requests_for, render_once

nglview = pytest.importorskip("nglview")


def test_camera_orientation_muted_without_the_accessor(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        v = nglview.NGLWidget()
    render_once(render_nglview(), v, widget_session)
    assert {
        "shinywidgets": "mute",
        "traits": ["_camera_orientation"],
    } in mute_requests_for(flush_to_browser(), v)


def test_camera_orientation_flows_with_the_accessor(
    widget_session: Session, flush_to_browser: Flush
) -> None:
    with session_context(widget_session):
        v = nglview.NGLWidget()
    render_once(render_nglview(listen_to=["camera_orientation"]), v, widget_session)
    assert mute_requests_for(flush_to_browser(), v) == [
        {"shinywidgets": "mute", "traits": []}
    ]


def test_camera_orientation_accessor_follows_the_trait(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        v = nglview.NGLWidget()
    # rate_delay=0: the accessor debounces by default, and this test's sets
    # must publish synchronously (no running loop to schedule a timer on)
    r = render_nglview(listen_to=["camera_orientation"], rate_delay=0)
    render_once(r, v, widget_session)
    with session_context(widget_session):
        assert r.camera_orientation() is None  # no camera movement yet
        v._camera_orientation = [1.0] * 16
        assert r.camera_orientation() == [1.0] * 16
