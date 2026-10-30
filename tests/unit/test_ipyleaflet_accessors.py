from __future__ import annotations

import ipywidgets
import pytest
import shinywidgets._ipyleaflet as si
from shiny import Session
from shiny.session import session_context
from shiny.types import SilentException
from shinywidgets import render_ipyleaflet

ipyleaflet = pytest.importorskip("ipyleaflet")
import ipyleaflet as L  # noqa: E402


def leaflet_map(session: Session, **kwargs) -> "L.Map":
    with session_context(session):
        return L.Map(center=(52, 0), zoom=4, **kwargs)


def renderer(m: "L.Map") -> "render_ipyleaflet[object]":
    r = render_ipyleaflet()
    r._widget = m  # stands in for _render()
    r._accessors.on_render(m)
    return r


def set_viewport(m: "L.Map") -> None:
    # What the browser syncs after a pan/zoom (one message; traitlets notifies
    # bounds once)
    for trait, value in (
        ("south", 51.0),
        ("west", -1.0),
        ("north", 53.0),
        ("east", 1.0),
    ):
        m.set_trait(trait, value)


def test_bounds_is_empty_until_the_browser_reports(widget_session: Session) -> None:
    r = renderer(leaflet_map(widget_session))
    with pytest.raises(SilentException):
        r.bounds()
    m = r.widget
    assert isinstance(m, L.Map)
    set_viewport(m)
    assert r.bounds() == ((51.0, -1.0), (53.0, 1.0))


def test_zoom_and_center_seed_and_follow(widget_session: Session) -> None:
    r = renderer(leaflet_map(widget_session))
    assert r.zoom() == 4 and r.center() == [52, 0]
    m = r.widget
    assert isinstance(m, L.Map)
    m.zoom = 7.5
    m.center = [40, -74]
    assert r.zoom() == 7.5 and r.center() == [40, -74]


def test_clicked_reports_clicks_only(widget_session: Session) -> None:
    r = renderer(leaflet_map(widget_session))
    assert r.clicked() is None
    m = r.widget
    assert isinstance(m, L.Map)
    # What the browser sends; other interaction types are ignored
    m._handle_custom_msg(
        {"event": "interaction", "type": "mousemove", "coordinates": [1, 2]}, []
    )
    assert r.clicked() is None
    m._handle_custom_msg(
        {"event": "interaction", "type": "click", "coordinates": [52.5, -0.1]}, []
    )
    assert r.clicked() is not None
    assert r.clicked()["coordinates"] == [52.5, -0.1]
    r._accessors.on_render(leaflet_map(widget_session))
    assert r.clicked() is None  # events reset on re-render


def test_drawn_features_follows_the_draw_control(widget_session: Session) -> None:
    m = leaflet_map(widget_session)
    with session_context(widget_session):
        m.add(L.DrawControl())
    r = renderer(m)
    assert r.drawn_features() == []
    feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-0.1, 52.5]},
        "properties": {},
    }
    control = si.draw_control_of(m)
    assert control is not None
    control.data = [feature]
    assert r.drawn_features() == [feature]
    # Replacing the control set re-attaches; dropping the DrawControl errors
    # loudly (traitlets propagates observer exceptions to the assignment, so
    # the TypeError surfaces there rather than at the next read)
    with pytest.raises(TypeError, match="DrawControl"):
        m.controls = ()
    with session_context(widget_session):
        m.add(L.DrawControl())
    assert r.drawn_features() == []


def test_drawn_features_requires_a_draw_control(widget_session: Session) -> None:
    r = renderer(leaflet_map(widget_session))
    with pytest.raises(TypeError, match="DrawControl"):
        r.drawn_features()


def test_accessors_reject_non_ipyleaflet_widgets(widget_session: Session) -> None:
    # render_leafmap with a non-ipyleaflet backend hits the same guard
    with session_context(widget_session):
        w = ipywidgets.IntSlider()
    for spec in si.IPYLEAFLET_ACCESSORS:
        with pytest.raises(TypeError, match="ipyleaflet map"):
            spec.attach(w, lambda raw: None)
