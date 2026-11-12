from __future__ import annotations

import asyncio
from typing import List

import numpy as np
import pytest
import shinywidgets._lonboard as sl
from shiny import Session, reactive
from shiny.session import session_context
from shinywidgets import render_lonboard
from shinywidgets._accessors import Accessors

from tests.unit.test_accessors import FakeSchedule

pytest.importorskip(
    "lonboard",
    reason="lonboard isn't installed (e.g., it lacks wheels for this Python version)",
)


def flush() -> None:
    asyncio.get_event_loop().run_until_complete(reactive.flush())


import geoarrow.rust.core as gr  # noqa: E402
import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402
from arro3.core import Table  # noqa: E402
from lonboard import Map, ScatterplotLayer  # noqa: E402
from lonboard.view_state import MapViewState  # noqa: E402
from shapely.geometry import Point  # noqa: E402


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


def test_view_state_stream_debounces_by_default(widget_session: Session) -> None:
    # The browser syncs `view_state` on every deck.gl `onViewStateChange`
    # (each animation frame of a pan or zoom), so `view_state()` debounces
    # by default and the renderer's rate_policy/rate_delay kwargs apply to it.
    assert sl.VIEW_STATE.rate_policy == "debounce"

    m = lon_map(widget_session)
    seed = m.view_state
    s = FakeSchedule()
    a = Accessors([sl.VIEW_STATE], schedule=s)
    a.on_render(m)
    assert a.read("view_state") == seed  # the seed doesn't wait out the debounce
    m.view_state = MapViewState(longitude=1.0, latitude=2.0, zoom=5.0)
    m.view_state = MapViewState(longitude=3.0, latitude=4.0, zoom=6.0)
    assert a.read("view_state") == seed  # mid-gesture values are held
    s.fire()
    assert a.read("view_state") == MapViewState(longitude=3.0, latitude=4.0, zoom=6.0)


def test_view_state_rate_delay_zero_disables_the_debounce(
    widget_session: Session,
) -> None:
    m = lon_map(widget_session)
    a = Accessors([sl.VIEW_STATE], rate_delay=0, schedule=FakeSchedule())
    a.on_render(m)
    # The render-time attach already seeded the observer, so the set below
    # goes through the limiter (a set before attach would be the seed)
    a.read("view_state")
    m.view_state = MapViewState(longitude=1.0, latitude=2.0, zoom=5.0)
    assert a.read("view_state") == MapViewState(longitude=1.0, latitude=2.0, zoom=5.0)


def test_selected_reports_the_most_recent_pick_across_layers(
    widget_session: Session,
) -> None:
    l1, l2 = layer(widget_session), layer(widget_session)
    m = lon_map(widget_session, l1, l2)
    emitted: List[object] = []
    sl.SELECTED.attach(m, emitted.append)
    assert emitted == [None]  # state kind: seeds, and nothing is picked yet
    l2.selected_index = 4
    l1.selected_index = 1
    assert emitted == [None, 4, 1]


def test_selected_seeds_a_pick_made_before_attach(
    widget_session: Session,
) -> None:
    lay = layer(widget_session)
    m = lon_map(widget_session, lay)
    lay.selected_index = 2  # a pick that landed before the accessor attached
    emitted: List[object] = []
    detach = sl.SELECTED.attach(m, emitted.append)
    assert emitted == [2]
    detach()


def test_selected_seed_with_several_picked_layers_is_none(
    widget_session: Session,
) -> None:
    # Each layer retains its own pick with no timestamp to order them, so
    # the seed is a pick only when exactly one layer holds one.
    l1, l2, l3 = layer(widget_session), layer(widget_session), layer(widget_session)
    l1.selected_index = 1
    l2.selected_index = 2
    m = lon_map(widget_session, l1, l2, l3)
    emitted: List[object] = []
    detach1 = sl.SELECTED.attach(m, emitted.append)
    assert emitted == [None]  # ambiguous: two layers hold picks
    detach1()

    l1.selected_index = None
    emitted.clear()
    detach2 = sl.SELECTED.attach(m, emitted.append)
    assert emitted == [2]  # unambiguous: only l2 holds a pick
    detach2()


def test_selected_reattaches_when_layers_change(
    widget_session: Session,
) -> None:
    m = lon_map(widget_session)
    emitted: List[object] = []
    detach = sl.SELECTED.attach(m, emitted.append)
    assert emitted == [None]  # the seed
    new_layer = layer(widget_session)
    m.add_layer(new_layer)
    new_layer.selected_index = 2
    assert emitted == [None, 2]
    # Removing a layer moves its observer off it, so its picks stop reporting
    m.layers = m.layers[:1]
    new_layer.selected_index = 4
    assert emitted == [None, 2]
    detach()
    m.layers[0].selected_index = 0
    assert emitted == [None, 2]


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


def test_renderer_reads_and_retention(widget_session: Session) -> None:
    m = lon_map(widget_session)
    r = render_lonboard()
    r._widget = m  # stands in for _render()
    r._accessors.on_render(m)
    assert r.clicked() is None and r.selected() is None
    assert isinstance(r.view_state(), MapViewState)
    assert r.selected_bounds() is None

    m._handle_custom_msg({"kind": "on-click", "coordinate": [1.0, 2.0]}, [])
    assert r.clicked() == (1.0, 2.0)
    m.layers[0].selected_index = 3
    assert r.selected() == 3

    # A re-render retains the last click (it still happened), while the
    # state accessors re-seed from the new widget -- a fresh map has no
    # pick, so selected() re-seeds to None. The old map's click channel
    # closes again.
    r._accessors.on_render(lon_map(widget_session))
    assert not m._has_click_handlers
    assert r.clicked() == (1.0, 2.0) and r.selected() is None
    assert isinstance(r.view_state(), MapViewState)


def test_clicked_is_plain_state() -> None:
    from shinywidgets._lonboard import CLICKED

    assert CLICKED.kind == "state"


GDF = gpd.GeoDataFrame(
    {"name": list("abcde"), "value": [10, 20, 30, 40, 50]},
    geometry=[Point(20 + i, 40 + i) for i in range(5)],
    crs="EPSG:4326",
)


def geo_map(widget_session: Session, *layers) -> Map:
    with session_context(widget_session):
        return Map(list(layers) or [ScatterplotLayer.from_geopandas(GDF)])


def rows_render(widget_session: Session, m: Map) -> render_lonboard:
    r = render_lonboard()
    r._widget = m  # stands in for _render()
    r._accessors.on_render(m)
    return r


def test_selected_rows_default_frame_follows_the_pick(
    widget_session: Session,
) -> None:
    m = geo_map(widget_session)
    r = rows_render(widget_session, m)

    # No pick yet: an empty frame with the layer's columns
    out = r.selected_rows()
    assert isinstance(out, gpd.GeoDataFrame)
    assert len(out) == 0
    assert list(out.columns) == list(GDF.columns)

    m.layers[0].selected_index = 2
    out = r.selected_rows()
    assert isinstance(out, gpd.GeoDataFrame)
    assert out["name"].tolist() == ["c"]
    assert out["value"].tolist() == [30]
    assert out.geometry.iloc[0].equals(GDF.geometry.iloc[2])
    # The reconstructed frame can't carry the original index
    assert isinstance(out.index, pd.RangeIndex)


def test_selected_rows_explicit_frame_keeps_its_type(
    widget_session: Session,
) -> None:
    import polars as pl

    m = geo_map(widget_session)
    r = rows_render(widget_session, m)
    m.layers[0].selected_index = 1

    out = r.selected_rows(pl.DataFrame({"value": [10, 20, 30, 40, 50]}))
    assert isinstance(out, pl.DataFrame)
    assert out["value"].to_list() == [20]

    out = r.selected_rows(pd.DataFrame({"name": list("abcde")}))
    assert isinstance(out, pd.DataFrame)
    assert out["name"].tolist() == ["b"]


def test_selected_rows_explicit_frame_no_pick_is_empty(
    widget_session: Session,
) -> None:
    m = geo_map(widget_session)
    r = rows_render(widget_session, m)
    df = pd.DataFrame({"name": list("abcde")})
    out = r.selected_rows(df)
    assert isinstance(out, pd.DataFrame)
    assert len(out) == 0
    assert list(out.columns) == ["name"]


def test_selected_rows_several_pickable_layers_raise(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        layers = [ScatterplotLayer.from_geopandas(GDF) for _ in range(2)]
    m = geo_map(widget_session, *layers)
    r = rows_render(widget_session, m)
    m.layers[0].selected_index = 1
    with pytest.raises(ValueError, match="selected_index"):
        r.selected_rows()


def test_selected_rows_ignores_non_pickable_layers(
    widget_session: Session,
) -> None:
    # A non-pickable layer can never supply a pick, so it doesn't make the
    # default frame ambiguous
    with session_context(widget_session):
        pick = ScatterplotLayer.from_geopandas(GDF)
        backdrop = ScatterplotLayer.from_geopandas(GDF, pickable=False)
    m = geo_map(widget_session, pick, backdrop)
    r = rows_render(widget_session, m)
    pick.selected_index = 2
    assert r.selected_rows()["name"].tolist() == ["c"]


def test_selected_rows_pickable_toggle_invalidates_readers(
    widget_session: Session,
) -> None:
    # Toggling `pickable` at runtime changes which layers a pick can come
    # from, so readers take a dependency on every layer's pickable trait:
    # enabling a second pickable layer turns the default frame ambiguous
    with session_context(widget_session):
        pick = ScatterplotLayer.from_geopandas(GDF)
        backdrop = ScatterplotLayer.from_geopandas(GDF, pickable=False)
    m = geo_map(widget_session, pick, backdrop)
    r = rows_render(widget_session, m)
    pick.selected_index = 2  # row "c"

    runs: List[List[str]] = []
    errors: List[bool] = []
    with session_context(widget_session):

        @reactive.effect
        def _() -> None:
            try:
                runs.append(r.selected_rows()["name"].tolist())
            except ValueError:
                errors.append(True)

        flush()
        assert runs == [["c"]] and errors == []
        backdrop.pickable = True
        flush()
        assert errors == [True]
        backdrop.pickable = False
        flush()
        assert runs == [["c"], ["c"]]


def test_selected_rows_follows_layer_table_replacement(
    widget_session: Session,
) -> None:
    # A long-lived map can have a layer's data replaced in place; readers
    # take a dependency on the table, so the picked row follows the
    # replacement (positionally -- row 1 of the new data)
    m = geo_map(widget_session)
    r = rows_render(widget_session, m)
    m.layers[0].selected_index = 1  # row "b"

    runs: List[List[str]] = []
    with session_context(widget_session):

        @reactive.effect
        def _() -> None:
            runs.append(r.selected_rows()["name"].tolist())

        flush()
        assert runs == [["b"]]

        other = ScatterplotLayer.from_geopandas(
            gpd.GeoDataFrame(
                {"name": list("vwxyz"), "value": [1, 2, 3, 4, 5]},
                geometry=[Point(i, i) for i in range(5)],
                crs="EPSG:4326",
            )
        )
        m.layers[0].table = other.table
        flush()
        assert runs == [["b"], ["w"]]


def test_selected_rows_layer_without_a_table_raises(
    widget_session: Session,
) -> None:
    # BitmapLayer has a selected_index trait (so the attach treats it as
    # pickable) but no data table to reconstruct a frame from
    from lonboard import BitmapLayer

    with session_context(widget_session):
        m = Map(
            BitmapLayer(
                image="https://example.com/tile.png",
                bounds=[-180, -85, 180, 85],
            )
        )
    r = rows_render(widget_session, m)
    with pytest.raises(TypeError, match="df="):
        r.selected_rows()


def test_selected_rows_default_frame_needs_geopandas(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    m = geo_map(widget_session)
    r = rows_render(widget_session, m)
    m.layers[0].selected_index = 0
    monkeypatch.setitem(sys.modules, "geopandas", None)
    with pytest.raises(ImportError, match="geopandas"):
        r.selected_rows()
