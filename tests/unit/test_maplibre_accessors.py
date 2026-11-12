from __future__ import annotations

import pytest
import shinywidgets._maplibre as sm
from shiny import Session
from shiny.session import session_context
from shiny.types import SilentException

pytest.importorskip("maplibre")
from maplibre.ipywidget import MapWidget  # noqa: E402
from shinywidgets import render_maplibre  # noqa: E402

VIEW_STATE = {
    "center": {"lng": 2.35, "lat": 48.86},
    "zoom": 11,
    "bounds": {"_sw": {"lng": 2.2, "lat": 48.8}, "_ne": {"lng": 2.5, "lat": 48.9}},
    "bearing": 0,
    "pitch": 0,
}
CLICK = {"lng": 2.3522, "lat": 48.8566}
FEATURE = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [2.35, 48.86]},
    "properties": {},
}


def map_widget(session: Session, **kwargs) -> MapWidget:
    with session_context(session):
        return MapWidget(**kwargs)


def renderer(w: MapWidget) -> "render_maplibre[MapWidget]":
    r = render_maplibre()
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    return r


def test_view_state_cancels_until_the_browser_reports(
    widget_session: Session,
) -> None:
    r = renderer(map_widget(widget_session))
    with pytest.raises(SilentException):
        r.view_state()
    m = r.widget
    assert isinstance(m, MapWidget)
    m.set_trait("view_state", VIEW_STATE)
    assert r.view_state() == VIEW_STATE


def test_view_state_is_reseeded_when_the_new_map_reports(
    widget_session: Session,
) -> None:
    r = renderer(map_widget(widget_session))
    m = r.widget
    assert isinstance(m, MapWidget)
    m.set_trait("view_state", VIEW_STATE)
    assert r.view_state() == VIEW_STATE
    # A re-render keeps the old value until the new map's browser reports
    m2 = map_widget(widget_session)
    r._accessors.on_render(m2)
    assert r.view_state() == VIEW_STATE
    new_state = {**VIEW_STATE, "zoom": 12}
    m2.set_trait("view_state", new_state)
    assert r.view_state() == new_state


def test_view_state_seeds_from_a_widget_that_already_reported(
    widget_session: Session,
) -> None:
    # A cached (e.g. shared-lifetime) widget may already hold a browser
    # report; the first read must see it
    m = map_widget(widget_session)
    m.set_trait("view_state", VIEW_STATE)
    r = renderer(m)
    assert r.view_state() == VIEW_STATE


def test_clicked_is_none_until_the_first_click(widget_session: Session) -> None:
    r = renderer(map_widget(widget_session))
    assert r.clicked() is None
    m = r.widget
    assert isinstance(m, MapWidget)
    m.set_trait("clicked", CLICK)
    assert r.clicked() == CLICK


def test_clicked_is_kept_across_a_rerender(widget_session: Session) -> None:
    r = renderer(map_widget(widget_session))
    m = r.widget
    assert isinstance(m, MapWidget)
    m.set_trait("clicked", CLICK)
    assert r.clicked() == CLICK
    # The new map's {} ("no click yet") must not re-seed the kept click...
    m2 = map_widget(widget_session)
    r._accessors.on_render(m2)
    assert r.clicked() == CLICK
    # ...until the user clicks the new map
    click2 = {"lng": 0.0, "lat": 0.0}
    m2.set_trait("clicked", click2)
    assert r.clicked() == click2


def test_drawn_features_starts_empty_and_follows_the_trait(
    widget_session: Session,
) -> None:
    r = renderer(map_widget(widget_session))
    assert r.drawn_features() == []
    m = r.widget
    assert isinstance(m, MapWidget)
    m.set_trait(
        "draw_feature_collection_all",
        {"type": "FeatureCollection", "features": [FEATURE]},
    )
    assert r.drawn_features() == [FEATURE]


def test_drawn_features_is_reseeded_on_rerender(widget_session: Session) -> None:
    r = renderer(map_widget(widget_session))
    m = r.widget
    assert isinstance(m, MapWidget)
    m.set_trait(
        "draw_feature_collection_all",
        {"type": "FeatureCollection", "features": [FEATURE]},
    )
    assert r.drawn_features() == [FEATURE]
    # Drawn shapes live on the map, so a re-render starts from the new map's
    # own (empty) set
    r._accessors.on_render(map_widget(widget_session))
    assert r.drawn_features() == []


def test_no_default_rate_policy() -> None:
    # The browser reports view_state once per completed gesture (load /
    # zoomend / moveend), and clicked/drawn only on discrete events, so none
    # of these stream continuously enough to declare a default
    for spec in sm.MAPLIBRE_ACCESSORS:
        assert spec.rate_policy is None
