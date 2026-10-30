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
    # Replacing the control set re-attaches; dropping the DrawControl
    # doesn't raise at attach (it runs during render), but the next read
    # raises
    m.controls = ()
    with pytest.raises(TypeError, match="DrawControl"):
        r.drawn_features()
    with session_context(widget_session):
        m.add(L.DrawControl())
    assert r.drawn_features() == []


def test_drawn_features_requires_a_draw_control(widget_session: Session) -> None:
    r = renderer(leaflet_map(widget_session))
    with pytest.raises(TypeError, match="DrawControl"):
        r.drawn_features()


def test_render_and_rerender_without_draw_control_never_raises(
    widget_session: Session,
) -> None:
    # on_render() re-attaches accessors that were read once; a missing
    # DrawControl must not break the map output, only the read
    r = renderer(leaflet_map(widget_session))
    with pytest.raises(TypeError, match="DrawControl"):
        r.drawn_features()
    m2 = leaflet_map(widget_session)  # still no DrawControl
    r._widget = m2
    r._accessors.on_render(m2)
    with pytest.raises(TypeError, match="DrawControl"):
        r.drawn_features()


def test_rerender_dropping_draw_control_renders_but_read_raises(
    widget_session: Session,
) -> None:
    m = leaflet_map(widget_session)
    with session_context(widget_session):
        m.add(L.DrawControl())
    r = renderer(m)
    assert r.drawn_features() == []  # read once, so re-renders re-attach
    # A re-render returning a map without a DrawControl renders fine...
    m2 = leaflet_map(widget_session)
    r._widget = m2
    r._accessors.on_render(m2)
    # ...and only drawn_features() raises, when read
    with pytest.raises(TypeError, match="DrawControl"):
        r.drawn_features()
    assert r.zoom() == 4  # the other accessors are unaffected


def test_accessors_reject_non_ipyleaflet_widgets(widget_session: Session) -> None:
    # render_leafmap with a non-ipyleaflet backend hits the same guard
    with session_context(widget_session):
        w = ipywidgets.IntSlider()
    for spec in si.IPYLEAFLET_ACCESSORS:
        with pytest.raises(TypeError, match="ipyleaflet map"):
            spec.attach(w, lambda raw: None)


def test_leafmap_ipyleaflet_backend_shares_the_accessors(
    widget_session: Session,
) -> None:
    from shinywidgets import render_leafmap

    # What leafmap.leafmap.Map is: an ipyleaflet.Map subclass defined in leafmap
    LeafmapMap = type("Map", (L.Map,), {"__module__": "leafmap.leafmap"})
    with session_context(widget_session):
        m = LeafmapMap(center=(52, 0), zoom=4)
    r = render_leafmap()
    r._widget = m  # stands in for _render()
    r._accessors.on_render(m)
    assert r.zoom() == 4 and r.center() == [52, 0]
    with pytest.raises(SilentException):
        r.bounds()
    set_viewport(m)
    assert r.bounds() == ((51.0, -1.0), (53.0, 1.0))


def test_leafmap_other_backends_raise_a_naming_type_error(
    widget_session: Session,
) -> None:
    from shinywidgets import render_leafmap

    r = render_leafmap()
    with session_context(widget_session):
        w = ipywidgets.IntSlider()  # stands in for a non-ipyleaflet backend
    r._widget = w
    r._accessors.on_render(w)
    with pytest.raises(TypeError, match="ipyleaflet map"):
        r.zoom()
