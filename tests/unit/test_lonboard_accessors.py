from __future__ import annotations

from typing import List

import numpy as np
import pytest
import shinywidgets._lonboard as sl
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_lonboard

pytest.importorskip(
    "lonboard",
    reason="lonboard isn't installed (e.g., it lacks wheels for this Python version)",
)

import geoarrow.rust.core as gr  # noqa: E402
from arro3.core import Table  # noqa: E402
from lonboard import Map, ScatterplotLayer  # noqa: E402
from lonboard.view_state import MapViewState  # noqa: E402


def layer(session: Session, n: int = 5) -> ScatterplotLayer:
    with session_context(session):
        coords = (np.linspace(-10, 10, n), np.linspace(-5, 5, n))
        table = Table.from_arrays(
            [gr.points(coords, crs="EPSG:4326")], names=["geometry"]
        )
        return ScatterplotLayer(table=table)


def lon_map(session: Session, *layers) -> Map:
    with session_context(session):
        return Map(list(layers) or [layer(session)])


def test_view_state_seeds_current_state(widget_session: Session) -> None:
    m = lon_map(widget_session)
    emitted: List[object] = []
    detach = sl.VIEW_STATE.attach(m, emitted.append)
    assert emitted == [m.view_state]
    assert isinstance(emitted[0], MapViewState)
    detach()
    m.view_state = MapViewState(longitude=1.0, latitude=2.0, zoom=5.0)
    assert len(emitted) == 1  # detached


def test_selected_index_reports_the_most_recent_pick_across_layers(
    widget_session: Session,
) -> None:
    l1, l2 = layer(widget_session), layer(widget_session)
    m = lon_map(widget_session, l1, l2)
    emitted: List[object] = []
    sl.SELECTED_INDEX.attach(m, emitted.append)
    assert emitted == []  # event kind: no seeding
    l2.selected_index = 4
    l1.selected_index = 1
    assert emitted == [4, 1]


def test_selected_index_reattaches_when_layers_change(
    widget_session: Session,
) -> None:
    m = lon_map(widget_session)
    emitted: List[object] = []
    detach = sl.SELECTED_INDEX.attach(m, emitted.append)
    new_layer = layer(widget_session)
    m.add_layer(new_layer)
    new_layer.selected_index = 2
    assert emitted == [2]
    detach()
    m.layers[0].selected_index = 0
    assert emitted == [2]


def test_selected_bounds_seeds_none_and_follows(widget_session: Session) -> None:
    m = lon_map(widget_session)
    emitted: List[object] = []
    sl.SELECTED_BOUNDS.attach(m, emitted.append)
    assert emitted == [None]
    m.selected_bounds = (-1.0, -2.0, 3.0, 4.0)
    assert emitted[-1] == (-1.0, -2.0, 3.0, 4.0)


def test_clicked_registers_and_unregisters_the_browser_channel(
    widget_session: Session,
) -> None:
    m = lon_map(widget_session)
    assert not m._has_click_handlers
    emitted: List[object] = []
    detach = sl.CLICKED.attach(m, emitted.append)
    assert m._has_click_handlers  # the browser now sends clicks
    # What the browser sends on a click
    m._handle_custom_msg({"kind": "on-click", "coordinate": [-0.1, 52.5]}, [])
    assert emitted == [(-0.1, 52.5)]
    detach()
    assert not m._has_click_handlers


def test_renderer_reads_and_event_reset(widget_session: Session) -> None:
    m = lon_map(widget_session)
    r = render_lonboard()
    r._widget = m  # stands in for _render()
    r._accessors.on_render(m)
    assert r.clicked() is None and r.selected_index() is None
    assert isinstance(r.view_state(), MapViewState)
    assert r.selected_bounds() is None

    m._handle_custom_msg({"kind": "on-click", "coordinate": [1.0, 2.0]}, [])
    assert r.clicked() == (1.0, 2.0)
    m.layers[0].selected_index = 3
    assert r.selected_index() == 3

    # A re-render resets the events (they referred to the old map) but not the
    # state accessors, which re-seed from the new widget
    r._accessors.on_render(lon_map(widget_session))
    assert r.clicked() is None and r.selected_index() is None
    assert isinstance(r.view_state(), MapViewState)
