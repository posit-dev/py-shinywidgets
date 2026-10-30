from __future__ import annotations

from typing import List

import shinywidgets._niivue as sn
import shinywidgets._render_widget as rw
from shiny import Session
from shiny.session import session_context

LOCATION_DATA = {
    "ax_cor_sag": 0,
    "frac": [0.5, 0.5, 0.5],
    "mm": [0.0, 0.0, 0.0],
    "vox": [45, 54, 45],
    "values": [12.3],
    "string": "...",
    "xy": [10, 10],
}


def make_nv(session: Session):
    from ipyniivue import NiiVue

    with session_context(session):
        return NiiVue()


def test_location_routes_through_the_library_dispatcher(
    widget_session: Session,
) -> None:
    nv = make_nv(widget_session)
    emitted: List[object] = []
    detach = sn.LOCATION.attach(nv, emitted.append)
    # What the browser sends on a crosshair move
    nv._handle_custom_msg({"event": "location_change", "data": LOCATION_DATA}, None)
    assert emitted == [LOCATION_DATA]
    detach()
    nv._handle_custom_msg({"event": "location_change", "data": LOCATION_DATA}, None)
    assert emitted == [LOCATION_DATA]


def test_location_is_debounced_by_default() -> None:
    assert sn.LOCATION.rate_policy == "debounce" and sn.LOCATION.rate_delay == 250


def test_renderer_location_round_trips_and_resets(widget_session: Session) -> None:
    nv = make_nv(widget_session)
    r = rw.render_niivue(rate_delay=0)  # skip the debounce wait
    r._widget = nv  # stands in for _render()
    r._accessors.on_render(nv)
    assert r.location() is None
    nv._handle_custom_msg({"event": "location_change", "data": LOCATION_DATA}, None)
    assert r.location() == LOCATION_DATA
    # Event semantics: a re-render resets the accessor to None
    r._accessors.on_render(nv)
    assert r.location() is None
