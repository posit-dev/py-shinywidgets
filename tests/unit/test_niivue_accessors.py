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

# The seed attach_location() emits from a widget whose crosshair was never
# moved (the trait's default is the volume center)
DEFAULT_SEED = {"frac": [0.5, 0.5, 0.5], "seeded": True}


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
    # Attach seeds the last synced crosshair position (the default here)
    assert emitted == [DEFAULT_SEED]
    # What the browser sends on a crosshair move
    nv._handle_custom_msg({"event": "location_change", "data": LOCATION_DATA}, None)
    assert emitted == [DEFAULT_SEED, LOCATION_DATA]
    detach()
    nv._handle_custom_msg({"event": "location_change", "data": LOCATION_DATA}, None)
    assert emitted == [DEFAULT_SEED, LOCATION_DATA]


def test_location_is_state_and_debounced_by_default() -> None:
    assert sn.LOCATION.kind == "state"
    # Attached at render like every accessor, which is what lets the seed
    # reach a reader gated behind e.g. a button
    assert sn.LOCATION.rate_policy == "debounce" and sn.LOCATION.rate_delay == 0.25


def test_seed_reflects_the_pre_attach_position(widget_session: Session) -> None:
    nv = make_nv(widget_session)
    # A crosshair move synced from the frontend before anything read the
    # accessor (set_state writes _trait_values directly, swallowing the
    # notification, which is why the stream still comes from
    # on_location_change)
    nv.scene._trait_values.update({"crosshair_pos": [0.1, 0.2, 0.3]})
    r = rw.render_niivue()
    r._widget = nv  # stands in for _render()
    r._accessors.on_render(nv)
    assert r.location() == {"frac": [0.1, 0.2, 0.3], "seeded": True}


def test_seed_skipped_when_no_position_is_known(widget_session: Session) -> None:
    nv = make_nv(widget_session)
    nv.scene._trait_values.update({"crosshair_pos": None})
    r = rw.render_niivue(rate_delay=0)  # skip the debounce wait
    r._widget = nv  # stands in for _render()
    r._accessors.on_render(nv)
    assert r.location() is None
    # And the stream still attaches and flows
    nv._handle_custom_msg({"event": "location_change", "data": LOCATION_DATA}, None)
    assert r.location() == LOCATION_DATA


def test_renderer_location_round_trips_and_follows_rerender(
    widget_session: Session,
) -> None:
    nv = make_nv(widget_session)
    r = rw.render_niivue(rate_delay=0)  # skip the debounce wait
    r._widget = nv  # stands in for _render()
    r._accessors.on_render(nv)
    # State semantics: attaching at render seeds the current position
    assert r.location() == DEFAULT_SEED
    # The stream still flows post-attach via on_location_change
    nv._handle_custom_msg({"event": "location_change", "data": LOCATION_DATA}, None)
    assert r.location() == LOCATION_DATA
    # A re-render keeps the value until the new widget reports; its attach
    # seeds its own position (a fresh widget sits at the volume center)
    nv2 = make_nv(widget_session)
    r._widget = nv2
    r._accessors.on_render(nv2)
    assert r.location() == DEFAULT_SEED
    # The old widget's handler is gone
    nv._handle_custom_msg({"event": "location_change", "data": LOCATION_DATA}, None)
    assert r.location() == DEFAULT_SEED
    nv2._handle_custom_msg({"event": "location_change", "data": LOCATION_DATA}, None)
    assert r.location() == LOCATION_DATA
