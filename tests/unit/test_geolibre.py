from __future__ import annotations

import pytest

pytest.importorskip(
    "geolibre",
    reason="geolibre isn't installed (it requires Python >= 3.11)",
)

from geolibre import Map
from shiny import Session
from shiny.session import session_context
from shinywidgets._render_widget_base import set_layout_defaults


def geolibre_map(session: Session, **kwargs: object) -> Map:
    with session_context(session):
        return Map(**kwargs)  # type: ignore[arg-type]


def test_default_height_fills(widget_session: Session) -> None:
    w = geolibre_map(widget_session)
    _, fill = set_layout_defaults(w)
    assert fill is True
    # The embedded app styles its <iframe> from the height trait (once, when
    # it loads), so a filling output sizes the iframe to its container
    assert w.height == "100%"


def test_explicit_widget_height_disables_fill(widget_session: Session) -> None:
    w = geolibre_map(widget_session, height="600px")
    _, fill = set_layout_defaults(w)
    assert fill is False
    assert w.height == "600px"


def test_layout_trait_is_geolibres_own(widget_session: Session) -> None:
    # geolibre reuses the `layout` trait name for the app's chrome
    # ("embed"/"full"/"maponly"), shadowing ipywidgets' Layout widget. Make
    # sure set_layout_defaults() doesn't mistake it for a Layout.
    w = geolibre_map(widget_session, layout="maponly")
    assert isinstance(w.layout, str)
    _, fill = set_layout_defaults(w)
    assert fill is True
